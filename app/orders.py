"""Shared order service used by both the web API and the WhatsApp bot."""
from . import db, menu
from .config import DELIVERY_ZONES, FREE_DELIVERY_ABOVE


class OrderError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def delivery_fee(km: float, subtotal: float = 0.0) -> dict | None:
    """Quote only — no min-order enforcement (for the web UI to display live)."""
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


def create_order(phone: str, name: str, order_type: str, items: list[dict],
                 address: str | None = None, km: float | None = None,
                 payment_method: str = "cod", instructions: str | None = None,
                 scheduled_at: str | None = None) -> dict:
    if order_type not in ("delivery", "pickup"):
        raise OrderError("Invalid order_type", 400)

    lines, subtotal = build_lines(items)

    delivery_fee = 0.0
    if order_type == "delivery":
        if km is None:
            raise OrderError("Delivery distance is required", 400)
        quote = delivery_quote(km, subtotal)
        delivery_fee = quote["fee"]

    total = subtotal + delivery_fee
    cid = db.upsert_customer(phone, name, address)
    oid = db.create_order(cid, order_type, subtotal, delivery_fee, total,
                          payment_method, instructions, lines)
    return {"order_id": oid, "status": "new", "subtotal": round(subtotal, 2),
            "delivery_fee": delivery_fee, "total": round(total, 2)}
