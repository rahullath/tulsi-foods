"""Live delivery-fee estimates for checkout display.

Quotes come from Borzo's `calculate-order` (the real courier price for the
pin's location) — not the old distance-zone table. The zone table is kept as
the availability + minimum-order source and as an offline fallback.

Free-delivery is currently PAUSED (config.FREE_DELIVERY_ENABLED = False), so
every delivery shows its live fee. Zone fallback respects the same flag so the
two paths never disagree.

Quotes are cached briefly (5 min, bucketed by rounded coords + subtotal) so a
pin drag doesn't hammer the courier API for every pixel move.
"""
import time

from ..config import DELIVERY_ZONES, FREE_DELIVERY_ENABLED

_TTL_S = 300
_cache: dict[tuple, dict] = {}


def _zone_quote(lat: float, lng: float, subtotal: float, km_hint: float | None = None) -> dict:
    """Zone-table quote used as fallback / availability gate. Min-order and
    serviceability come from here; the fee is a rough estimate only."""
    from ..orders import _haversine_m, delivery_fee
    from .config import PICKUP_LAT, PICKUP_LNG

    km = km_hint if km_hint is not None else _haversine_m(float(lat), float(lng), PICKUP_LAT, PICKUP_LNG) / 1000
    zone = next((z for z in DELIVERY_ZONES if km <= z["max_km"]), None)
    if not zone:
        return {"serviceable": False, "fee": None, "provider": "zones", "km": km}
    if FREE_DELIVERY_ENABLED and subtotal >= FREE_DELIVERY_ABOVE:
        fee = 0.0
    else:
        fee = zone["fee"]
    q = delivery_fee(km, subtotal) or {}
    return {
        "serviceable": True, "fee": fee, "zone": zone["name"], "min_order": zone["min_order"],
        "km": km, "provider": "zones", "note": "estimate",
    }


def estimate(lat: float, lng: float, subtotal: float = 0.0,
             address: str | None = None, km_hint: float | None = None) -> dict:
    """Return the best delivery-fee estimate for a pin.

    Prefers Borzo's live quote; falls back to the zone table on any API
    failure. Never raises — checkout must not break because the courier API
    hiccuped. Includes `min_order`/`serviceable` from the zone gate.
    """
    lat, lng = float(lat), float(lng)
    key = (round(lat, 2), round(lng, 2), subtotal // 100)
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit["at"] < _TTL_S:
        return {k: v for k, v in hit.items() if k != "at"}

    result = _zone_quote(lat, lng, subtotal, km_hint)
    try:
        from .borzo import calculate_order as borzo_calculate
        q = borzo_calculate(
            delivery_address=address or "Customer delivery address",
            items=[{"qty": 1, "name": "food order"}],
            delivery_lat=str(lat), delivery_lng=str(lng), total=subtotal,
        )
        fee = float(q.get("payment_amount") or q.get("delivery_fee_amount") or 0)
        if fee > 0 and result.get("serviceable"):
            result["fee"] = round(fee)
            result["provider"] = "borzo"
            result["note"] = "live courier rate"
    except Exception:
        pass  # keep the zone fallback

    result["at"] = now
    _cache[key] = result
    return {k: v for k, v in result.items() if k != "at"}