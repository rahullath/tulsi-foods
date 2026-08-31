"""Outbound calls to Petpooja's PetpoojaOnlineOrdering API (V2.1.0).

Mirrors app/delivery/borzo.py's shape: raise on failure, return a plain
dict on success. All calls are no-ops upstream of this module unless
PETPOOJA_APP_KEY is set — see the callers in app/orders.py and
app/webhooks.py.
"""
import logging

import httpx

from .config import (
    PETPOOJA_ACCESS_TOKEN,
    PETPOOJA_APP_KEY,
    PETPOOJA_APP_SECRET,
    PETPOOJA_FETCH_MENU_URL,
    PETPOOJA_REST_ID,
    PETPOOJA_RIDER_STATUS_URL,
    PETPOOJA_SAVE_ORDER_URL,
    PETPOOJA_UPDATE_ORDER_STATUS_URL,
)
from .mapping import order_to_save_order_payload

log = logging.getLogger("petpooja")


class PetpoojaError(Exception):
    """Raised when a Petpooja API call fails. Carries payload/response for debugging."""

    def __init__(self, step: str, payload: dict, response: dict | str):
        self.step = step
        self.payload = payload
        self.response = response
        super().__init__(f"{step} failed: {response}")


def _auth_fields() -> dict:
    return {
        "app_key": PETPOOJA_APP_KEY,
        "app_secret": PETPOOJA_APP_SECRET,
        "access_token": PETPOOJA_ACCESS_TOKEN,
    }


def is_configured() -> bool:
    return bool(PETPOOJA_APP_KEY and PETPOOJA_APP_SECRET and PETPOOJA_ACCESS_TOKEN and PETPOOJA_REST_ID)


def save_order(order: dict, callback_url: str, gst_rate: float) -> dict:
    """Push a confirmed order into Petpooja POS as Pending; kitchen accepts on the terminal.

    Returns {"petpooja_order_id": str}. Raises PetpoojaError on failure.
    """
    payload = {
        **_auth_fields(),
        "restID": PETPOOJA_REST_ID,
        "orderinfo": order_to_save_order_payload(order, callback_url, gst_rate),
        "udid": "",
        "device_type": "Web",
    }
    with httpx.Client(timeout=20) as c:
        r = c.post(PETPOOJA_SAVE_ORDER_URL, json=payload)
        try:
            data = r.json()
        except ValueError:
            raise PetpoojaError("save_order", payload, r.text)
        if str(data.get("success")) != "1":
            raise PetpoojaError("save_order", payload, data)
    log.info("Petpooja save_order ok: our order %s -> petpooja order %s", order["id"], data.get("orderID"))
    return {"petpooja_order_id": str(data.get("orderID", ""))}


def cancel_order(client_order_id: int, reason: str) -> dict:
    """Tell Petpooja we cancelled an order on our side (status -1 only, per docs)."""
    payload = {
        **_auth_fields(),
        "restID": PETPOOJA_REST_ID,
        "orderID": "",
        "clientorderID": str(client_order_id),
        "cancelReason": reason,
        "status": "-1",
    }
    with httpx.Client(timeout=20) as c:
        r = c.post(PETPOOJA_UPDATE_ORDER_STATUS_URL, json=payload)
        try:
            data = r.json()
        except ValueError:
            raise PetpoojaError("update_order_status", payload, r.text)
    return data


def fetch_menu() -> dict:
    """Pull the current menu from Petpooja POS. Not yet wired into app/menu.py
    (data/menu.json is still the live catalog source) — see docs/HANDOFF.md
    for the reconciliation this needs before it can replace it."""
    with httpx.Client(timeout=30) as c:
        r = c.post(PETPOOJA_FETCH_MENU_URL, json={"restID": PETPOOJA_REST_ID})
        try:
            data = r.json()
        except ValueError:
            raise PetpoojaError("fetch_menu", {"restID": PETPOOJA_REST_ID}, r.text)
    return data


def push_rider_status(client_order_id: int, status: str, rider_name: str | None = None,
                       rider_phone: str | None = None) -> dict:
    """Tell Petpooja POS our courier's status, for self-delivery-style tracking
    on their end. status must be one of rider-assigned/rider-arrived/pickedup/delivered.
    Called from the Borzo webhook handler — see app/webhooks.py."""
    payload = {
        **_auth_fields(),
        "status": status,
        "order_id": str(client_order_id),
        "external_order_id": "",
        "rider_data": {"rider_name": rider_name or "", "rider_phone": rider_phone or ""},
    }
    with httpx.Client(timeout=20) as c:
        r = c.post(PETPOOJA_RIDER_STATUS_URL, json=payload)
        try:
            data = r.json()
        except ValueError:
            raise PetpoojaError("rider_status_update", payload, r.text)
    return data
