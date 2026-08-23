"""Shiprocket Quick (hyperlocal) API client.

Handles auth, serviceability checks, order creation, dispatch, and tracking.
Auth token is cached in SQLite and auto-refreshed on expiry.
"""
import json
import logging
from datetime import datetime, timedelta

import httpx

from ..config import DB_FILE
from .config import (
    DEFAULT_WEIGHT_KG,
    PICKUP_ADDRESS,
    PICKUP_LAT,
    PICKUP_LNG,
    PICKUP_PHONE,
    PICKUP_PINCODE,
    SHIPROCKET_API_EMAIL,
    SHIPROCKET_API_PASSWORD,
    SHIPROCKET_BASE_URL,
    SHIPROCKET_CHANNEL_ID,
)

log = logging.getLogger("shiprocket")

_TOKEN_TABLE = """
CREATE TABLE IF NOT EXISTS shiprocket_tokens (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    token TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def _conn():
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_token_table():
    conn = _conn()
    conn.executescript(_TOKEN_TABLE)
    conn.commit()
    conn.close()


def _get_cached_token() -> str | None:
    _ensure_token_table()
    conn = _conn()
    row = conn.execute("SELECT token, expires_at FROM shiprocket_tokens WHERE id=1").fetchone()
    conn.close()
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) > datetime.utcnow():
        return row["token"]
    return None


def _cache_token(token: str, expires_in_hours: int = 230) -> None:
    _ensure_token_table()
    expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()
    conn = _conn()
    conn.execute(
        "INSERT INTO shiprocket_tokens(id, token, expires_at) VALUES(1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET token=excluded.token, expires_at=excluded.expires_at",
        (token, expires_at),
    )
    conn.commit()
    conn.close()


def get_token() -> str:
    """Get a valid auth token, refreshing if needed."""
    cached = _get_cached_token()
    if cached:
        return cached
    if not SHIPROCKET_API_EMAIL or not SHIPROCKET_API_PASSWORD:
        raise RuntimeError("SHIPROCKET_API_EMAIL and SHIPROCKET_API_PASSWORD must be set in .env")
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SHIPROCKET_BASE_URL}/auth/login",
            json={"email": SHIPROCKET_API_EMAIL, "password": SHIPROCKET_API_PASSWORD},
        )
        r.raise_for_status()
        data = r.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(f"Shiprocket auth failed: {data}")
    _cache_token(token)
    log.info("Shiprocket auth token refreshed")
    return token


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_token()}"}


def check_serviceability(delivery_pincode: str, weight_kg: float = DEFAULT_WEIGHT_KG) -> list[dict]:
    """Check which hyperlocal couriers serve pickup→delivery pincode.

    Returns list of courier dicts with: courier_name, courier_company_id,
    estimated_delivery_days, freight_charge, rating, etc.
    Only returns local/hyperlocal couriers.
    """
    with httpx.Client(timeout=20) as c:
        r = c.get(
            f"{SHIPROCKET_BASE_URL}/courier/serviceability/",
            headers=_headers(),
            params={
                "pickup_postcode": PICKUP_PINCODE,
                "delivery_postcode": delivery_pincode,
                "weight": str(weight_kg),
                "cod": 0,
                "only_local": 1,
            },
        )
        r.raise_for_status()
        data = r.json()

    couriers = data.get("data", {}).get("available_courier_companies", [])
    return [
        {
            "courier_company_id": q["courier_company_id"],
            "courier_name": q["courier_name"],
            "estimated_delivery_days": q.get("estimated_delivery_days", ""),
            "freight_charge": q.get("freight_charge", 0),
            "rating": q.get("rating", 0),
            "etd": q.get("etd", ""),
            "is_hyperlocal": q.get("is_hyperlocal", False),
        }
        for q in couriers
    ]


def create_order(
    order_id: int,
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    delivery_pincode: str,
    items: list[dict],
    total: float,
    payment_method: str = "cod",
    cod_amount: float = 0,
) -> dict:
    """Create an order on Shiprocket. Returns {sr_order_id, shipment_id}.

    Items: [{"name": str, "sku": str, "units": int, "selling_price": float}]
    """
    order_items = []
    for it in items:
        order_items.append({
            "name": it["name"],
            "sku": it.get("sku", it["name"][:20]),
            "units": it.get("qty", 1),
            "selling_price": it["price"],
        })

    payload = {
        "order_id": str(order_id),
        "order_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "pickup_location": "Shop",
        "billing_customer_name": customer_name[:40],
        "billing_address": delivery_address[:200],
        "billing_pincode": delivery_pincode,
        "billing_city": "Chennai",
        "billing_state": "Tamil Nadu",
        "billing_country": "India",
        "billing_phone": customer_phone,
        "shipping_is_billing": True,
        "order_items": order_items,
        "payment_method": 0 if payment_method == "prepaid" else 1,  # 0=prepaid, 1=COD
        "cod_amount": cod_amount if payment_method == "cod" else 0,
        "sub_total": total,
        "length": 25,   # cm — food parcel defaults
        "breadth": 20,
        "height": 10,
        "weight": DEFAULT_WEIGHT_KG,
    }

    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SHIPROCKET_BASE_URL}/orders/create/adhoc",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    log.info("Shiprocket order created: %s", data.get("order_id"))
    return {
        "sr_order_id": data.get("order_id"),
        "shipment_id": data.get("shipment_id"),
    }


def assign_awb(sr_order_id: int) -> dict:
    """Assign AWB (courier tracking number) to a Shiprocket order.

    Returns {awb_code, courier_name, courier_company_id}.
    """
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SHIPROCKET_BASE_URL}/courier/assign/awb",
            headers=_headers(),
            json={"order_id": sr_order_id},
        )
        r.raise_for_status()
        data = r.json()

    response = data.get("response", {})
    if response.get("data", {}).get("awb_code"):
        awb_data = response["data"]
        log.info("AWB assigned: %s (courier: %s)", awb_data["awb_code"], awb_data.get("courier_name"))
        return {
            "awb_code": awb_data["awb_code"],
            "courier_name": awb_data.get("courier_name", ""),
            "courier_company_id": awb_data.get("courier_company_id"),
        }
    raise RuntimeError(f"AWB assignment failed: {data}")


def schedule_pickup(sr_order_id: int) -> dict:
    """Schedule pickup for a dispatched order. Returns pickup confirmation."""
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SHIPROCKET_BASE_URL}/courier/generate/pickup",
            headers=_headers(),
            json={"order_id": sr_order_id},
        )
        r.raise_for_status()
        data = r.json()

    log.info("Pickup scheduled for order %s: %s", sr_order_id, data)
    return data


def track_awb(awb_code: str) -> dict:
    """Track a shipment by AWB code.

    Returns {status_id, status_text, etd, current_location, courier_name, scans}.
    """
    with httpx.Client(timeout=20) as c:
        r = c.get(
            f"{SHIPROCKET_BASE_URL}/courier/track/awb/{awb_code}",
            headers=_headers(),
        )
        r.raise_for_status()
        data = r.json()

    scans = data.get("scans", [])
    current_location = scans[0]["location"] if scans else ""
    return {
        "status_id": data.get("current_status_id"),
        "status_text": data.get("current_status", ""),
        "etd": data.get("etd", ""),
        "current_location": current_location,
        "courier_name": data.get("courier_name", ""),
        "scans": scans,
    }


def track_order(order_id: str, channel_id: int | None = None) -> dict:
    """Track a shipment by Shiprocket order ID.

    Uses /courier/track?order_id=X which returns a tracking_data wrapper
    with shipment_track, shipment_track_activities, track_url, etd.
    """
    params: dict = {"order_id": order_id}
    if channel_id:
        params["channel_id"] = channel_id

    with httpx.Client(timeout=20) as c:
        r = c.get(
            f"{SHIPROCKET_BASE_URL}/courier/track",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        data = r.json()

    tracking = data[0].get("tracking_data", {}) if isinstance(data, list) and data else {}
    track = tracking.get("shipment_track", [{}])[0] if tracking.get("shipment_track") else {}
    activities = tracking.get("shipment_track_activities", [])
    current_location = activities[0]["location"] if activities else ""

    return {
        "status_text": track.get("current_status", ""),
        "origin": track.get("origin", ""),
        "destination": track.get("destination", ""),
        "edd": tracking.get("etd", ""),
        "track_url": tracking.get("track_url", ""),
        "current_location": current_location,
        "activities": activities,
    }


def get_pickup_addresses() -> list[dict]:
    """Return list of configured pickup locations on the account."""
    with httpx.Client(timeout=20) as c:
        r = c.get(
            f"{SHIPROCKET_BASE_URL}/settings/company/pickup",
            headers=_headers(),
        )
        r.raise_for_status()
        data = r.json()
    return data.get("data", {}).get("recent_addresses", [])


def dispatch_order(
    order_id: int,
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    delivery_pincode: str,
    items: list[dict],
    total: float,
    payment_method: str,
) -> dict:
    """Full dispatch flow: create order → assign AWB → schedule pickup.

    Returns {sr_order_id, awb_code, courier_name, ...}.
    """
    sr = create_order(
        order_id=order_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        delivery_pincode=delivery_pincode,
        items=items,
        total=total,
        payment_method=payment_method,
        cod_amount=total if payment_method == "cod" else 0,
    )

    awb = assign_awb(sr["sr_order_id"])

    # Attempt pickup scheduling (may fail if courier needs manual pickup time)
    try:
        pickup = schedule_pickup(sr["sr_order_id"])
    except Exception as e:
        log.warning("Pickup scheduling failed (non-fatal): %s", e)
        pickup = {}

    return {
        "sr_order_id": sr["sr_order_id"],
        "shipment_id": sr.get("shipment_id"),
        "awb_code": awb["awb_code"],
        "courier_name": awb["courier_name"],
        "tracking_url": f"https://shiprocket.in/tracking/{awb['awb_code']}",
    }
