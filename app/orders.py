"""Shared order service used by both the web API and the WhatsApp bot."""
import math
import re
from datetime import datetime, timedelta

from . import db, menu
from .config import (
    DELIVERY_ZONES,
    FREE_DELIVERY_ABOVE,
    GST_ENABLED,
    GST_RATE,
    PACKING_FEE,
    PACKING_FEE_LARGE_ORDER,
    PACKING_FEE_LARGE_ORDER_THRESHOLD,
)

ADDRESS_EDIT_WINDOW = timedelta(minutes=3)
MAX_SCHEDULE_AHEAD = timedelta(days=14)

_LANDMARK_RE = re.compile(r"\s*\(Landmark:\s*(.*?)\)\s*$", re.IGNORECASE)


def _validate_scheduled_at(scheduled_at: str | None) -> None:
    """scheduled_at arrives as a UTC ISO string (JS Date.toISOString())."""
    if not scheduled_at:
        return
    try:
        when = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise OrderError("Invalid scheduled time", 400)
    now = datetime.utcnow()
    if when < now - timedelta(minutes=5):
        raise OrderError("That time has already passed", 400)
    if when > now + MAX_SCHEDULE_AHEAD:
        raise OrderError("We only take orders up to 2 weeks ahead", 400)


def _split_landmark(address: str) -> tuple[str, str | None]:
    """Split the web checkout's "<address> (Landmark: <text>)" format back
    into its parts, for storing address book entries cleanly."""
    m = _LANDMARK_RE.search(address)
    if not m:
        return address, None
    return _LANDMARK_RE.sub("", address), m.group(1)


class OrderError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def delivery_fee(km: float, subtotal: float = 0.0) -> dict | None:
    """Quote only — no min-order enforcement (for the web UI to display live).
    Kept as fallback estimate when Shiprocket is unavailable."""
    zone = next((z for z in DELIVERY_ZONES if km <= z["max_km"]), None)
    if not zone:
        return None
    fee = 0.0 if subtotal >= FREE_DELIVERY_ABOVE else zone["fee"]
    return {"zone": zone["name"], "fee": fee, "min_order": zone["min_order"]}


def delivery_quote(km: float, subtotal: float) -> dict:
    quote = delivery_fee(km, subtotal)
    if quote is None:
        raise OrderError("We don't deliver there yet. You can pick up from the restaurant.", 400)
    if subtotal < quote["min_order"]:
        raise OrderError(
            f"Minimum order for {quote['zone']} is ₹{quote['min_order']}", 400
        )
    return quote


def check_pincode_serviceable(pincode: str) -> dict:
    """Check if a pincode is serviceable via Shiprocket Quick.

    Returns {serviceable: bool, couriers: list, fee_estimate: str}.
    Uses our zone logic for fee estimation since Indian pincodes cover broad areas.
    """
    try:
        from .delivery.shiprocket import check_serviceability
        couriers = check_serviceability(pincode)
        if couriers:
            cheapest = min(couriers, key=lambda c: c.get("freight_charge", 999))
            return {
                "serviceable": True,
                "couriers": couriers,
                "fee_estimate": f"~₹{int(cheapest.get('freight_charge', 0))}",
                "eta": cheapest.get("estimated_delivery_days", ""),
            }
    except Exception:
        pass
    # Fallback: assume serviceable if pincode looks valid (6 digits)
    if pincode and len(pincode) == 6 and pincode.isdigit():
        return {"serviceable": True, "couriers": [], "fee_estimate": "₹30–70", "eta": ""}
    return {"serviceable": False, "couriers": [], "fee_estimate": None, "eta": None}


def build_lines(items: list[dict]) -> tuple[list[dict], float]:
    """Validate item ids against today's availability; returns (lines, subtotal)."""
    lines, subtotal = [], 0.0
    for it in items:
        m = menu.get_item(it["item_id"])
        if not m:
            raise OrderError(f"Unknown item: {it['item_id']}", 400)
        if not menu.is_available(m["id"]):
            raise OrderError(f"'{m['name']}' is not available today", 409)
        price = float(m["price"])
        subtotal += price * it["qty"]
        lines.append({"item_id": m["id"], "name": m["name"], "price": price, "qty": it["qty"]})
    if not lines:
        raise OrderError("No items in order", 400)
    return lines, subtotal


def packing_fee_for(subtotal: float) -> float:
    if not PACKING_FEE:
        return 0.0
    return PACKING_FEE_LARGE_ORDER if subtotal >= PACKING_FEE_LARGE_ORDER_THRESHOLD else PACKING_FEE


def gst_for(taxable_base: float) -> float:
    """GST on item total + packing charge — delivery fee stays outside the
    taxable base, matching how the aggregator data tracks delivery "without
    tax" separately from the restaurant-service charge."""
    return round(taxable_base * GST_RATE, 2) if GST_ENABLED else 0.0


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def check_address(address: str | None, pincode: str | None,
                  lat: str | None, lng: str | None) -> tuple[bool, str | None]:
    """Best-effort heuristic: does this delivery address need a human look
    before booking a rider? Never raises — a geocoding failure just skips
    the distance check rather than blocking the order.

    The web checkout folds the landmark into `address` as "(Landmark: ...)"
    (see menu.html) — that's the deterministic marker checked for below.
    """
    if not address:
        return False, None
    if "(landmark:" not in address.lower():
        return True, "No landmark given — riders ask for one."
    if not lat or not lng:
        return True, "No GPS pin — only a typed address."
    try:
        from .delivery.shiprocket import geocode_address
        g_lat, g_lng = geocode_address(address, pincode or "")
        if g_lat and g_lng:
            dist = _haversine_m(float(lat), float(lng), float(g_lat), float(g_lng))
            if dist > 300:
                return True, f"Typed address and GPS pin are {int(dist)}m apart."
    except Exception:
        pass
    return False, None


def create_order(phone: str, name: str, order_type: str, items: list[dict],
                 address: str | None = None, km: float | None = None,
                 pincode: str | None = None,
                 payment_method: str = "cod", instructions: str | None = None,
                 scheduled_at: str | None = None,
                 lat: str | None = None, lng: str | None = None) -> dict:
    if order_type not in ("delivery", "pickup"):
        raise OrderError("Invalid order_type", 400)
    _validate_scheduled_at(scheduled_at)

    lines, subtotal = build_lines(items)

    delivery_fee = 0.0
    if order_type == "delivery":
        if km is not None:
            # Legacy km-based flow (WhatsApp bot fallback)
            quote = delivery_quote(km, subtotal)
            delivery_fee = quote["fee"]
        elif pincode:
            # Pincode-based flow: use zone estimate, actual fee set at dispatch
            zone_fee = delivery_fee_from_pincode(pincode, subtotal)
            delivery_fee = zone_fee
        else:
            raise OrderError("Delivery distance or pincode is required", 400)

    packing_fee = packing_fee_for(subtotal)
    gst_amount = gst_for(subtotal + packing_fee)
    total = subtotal + packing_fee + gst_amount + delivery_fee
    flagged, flag_reason = check_address(address, pincode, lat, lng)
    cid = db.upsert_customer(phone, name, address, pincode)
    oid = db.create_order(cid, order_type, subtotal, delivery_fee, total,
                          payment_method, instructions, lines,
                          delivery_address=address, delivery_pincode=pincode,
                          delivery_lat=lat, delivery_lng=lng,
                          scheduled_at=scheduled_at,
                          address_flagged=flagged, address_flag_reason=flag_reason,
                          packing_fee=packing_fee, gst_amount=gst_amount)
    if order_type == "delivery" and address:
        base_address, landmark = _split_landmark(address)
        try:
            db.add_customer_address(cid, base_address, landmark=landmark, lat=lat, lng=lng)
        except Exception:
            pass  # address book is a convenience, never block order creation

    # Kitchen alert (mom) — Telegram DMs her, never blocks the order flow.
    try:
        from .telegram import notify_new_order
        order_row = db.get_order(oid)
        if order_row is not None:
            notify_new_order(order_row)
    except Exception:
        pass

    return {"order_id": oid, "status": "new", "subtotal": round(subtotal, 2),
            "packing_fee": packing_fee, "gst_amount": gst_amount,
            "delivery_fee": delivery_fee, "total": round(total, 2)}


def edit_address(order_id: int, address: str, pincode: str | None = None,
                 lat: str | None = None, lng: str | None = None) -> dict:
    """Let a customer fix their delivery address within a short window after
    ordering — before the kitchen has started and before a rider is booked."""
    o = db.get_order(order_id)
    if not o:
        raise OrderError("Order not found", 404)
    if o["order_type"] != "delivery":
        raise OrderError("Only delivery orders have an address to change", 400)
    if o["status"] != "new":
        raise OrderError("Too late — the kitchen has already started on this order", 400)
    created = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() - created > ADDRESS_EDIT_WINDOW:
        raise OrderError("The 3-minute window to change the address has passed", 400)

    flagged, flag_reason = check_address(address, pincode or o.get("delivery_pincode"), lat, lng)
    db.update_order_address(order_id, address, lat, lng, address_flagged=flagged,
                            address_flag_reason=flag_reason)
    return {"ok": True, "order_id": order_id, "address": address}


def delivery_fee_from_pincode(pincode: str, subtotal: float) -> float:
    """Estimate delivery fee from pincode using zone logic.

    Since Indian pincodes cover broad areas, we use our zone estimates.
    The actual fee is calculated by Shiprocket at dispatch time.
    """
    # Map pincode prefix to approximate zones (Chennai-specific heuristic)
    # This is a rough estimate — real calculation happens at dispatch
    if subtotal >= FREE_DELIVERY_ABOVE:
        return 0.0
    # Default to Zone A fee as estimate; dispatch corrects if needed
    return DELIVERY_ZONES[0]["fee"]
