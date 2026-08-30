"""Telegram admin-alert notifier — tells Mom about new orders without Meta.

Unlike WhatsApp/SMS (customer channels), this is an internal kitchen alert that
works immediately: no Meta verification, no sender-ID registration, no cost.
Mom installs Telegram (free), taps her bot's /link, and every new order DMs her.

Disabled when TELEGRAM_BOT_TOKEN is empty (default). The admin page beep remains
the fallback so the kitchen still notices without Telegram.
"""
import logging

import httpx

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TULSI_ADMIN_URL

log = logging.getLogger("telegram")

API = "https://api.telegram.org/bot{token}"


def enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to mom's chat. Returns True if Telegram accepted it."""
    if not enabled():
        return False
    if len(text) > 4000:  # Telegram hard limit
        text = text[:3996] + "…"
    try:
        r = httpx.post(
            f"{API.format(token=TELEGRAM_BOT_TOKEN)}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
        data = r.json()
        ok = data.get("ok", False)
        if not ok:
            log.error("Telegram send failed: %s", data.get("description"))
        return ok
    except Exception:
        log.exception("Telegram send exception")
        return False


def notify_new_order(order: dict) -> bool:
    """Alert mom that a new order just came in."""
    oid = order["id"]
    customer = order.get("customer_name") or "Customer"
    total = order.get("total", 0)
    n_items = len(order.get("items") or [])
    lines = "\n".join(f"• {i['name']} × {i['qty']}" for i in (order.get("items") or [])[:8])
    extra = "" if n_items <= 8 else f"\n… and {n_items - 8} more"
    order_type = "Pickup" if order.get("order_type") == "pickup" else "Delivery"
    pay = (order.get("payment_method") or "cod").upper()
    text = (
        f"🛎 <b>New Order #{oid}</b> — {order_type}\n"
        f"👤 {customer}\n"
        f"💳 {pay} · ₹{total}\n"
        f"{lines}{extra}\n"
    )
    if order_type == "Delivery" and order.get("delivery_address"):
        text += f"📍 {order['delivery_address']}\n"
    if order.get("delivery_pincode"):
        text += f"📮 {order['delivery_pincode']}\n"
    text += f"<a href='{TULSI_ADMIN_URL}/?order={oid}'>Open order in admin →</a>"
    return send_message(text)


def notify_status(order: dict, status: str) -> bool:
    """Send mom a short status ping (dispatch/delivery completion)."""
    oid = order["id"]
    labels = {
        "preparing": "started cooking",
        "ready": "is ready to dispatch",
        "out_for_delivery": "rider on the way",
        "delivered": "marked delivered ✓",
        "cancelled": "was cancelled",
    }
    text = f"🛎 Order #{oid} {labels.get(status, status)}."
    return send_message(text)
