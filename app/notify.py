"""Customer notification dispatch — WhatsApp primary, SMS (Twilio) fallback.

WhatsApp: our own templates (app/whatsapp/templates.py, created on Meta by
templates.sync()) first, then the older Meta library template for that step
while ours is still in review, then free text (delivered only inside the 24 h
window). SMS only when WhatsApp is off, since unregistered (non-DLT) SMS to
Indian numbers is dropped — see docs/META_CONTINGENCY_PLAN.md §7.
"""
import logging

from .config import STORE_PICKUP_LINE, WHATSAPP_ACTIVE
from .whatsapp import templates as T

log = logging.getLogger("notify")


def _params(*values) -> list[dict]:
    # Template variables may not contain newlines/tabs or 4+ spaces in a row.
    return [{"type": "text", "text": " ".join(str(v).split()) or "-"} for v in values]


def _track_url(order: dict) -> str:
    return f"https://tulsifoods.app/track/{order.get('tracking_token') or order['id']}"


def _token(order: dict) -> str:
    return str(order.get("tracking_token") or order["id"])


def _send_wa(phone: str, attempts: list[tuple], fallback_text: str | None, order_id) -> bool:
    """Try each (template, params, button_suffix) in turn, then free text.
    Returns True if WhatsApp accepted any of them."""
    from . import whatsapp
    for name, params, button in attempts:
        try:
            whatsapp.client.send_template(phone, name, "en", params, button_url_suffix=button)
            return True
        except Exception as e:
            log.warning("template %s failed for order %s: %s", name, order_id, e)
    if not fallback_text:
        return False
    try:
        whatsapp.client.send_text(phone, fallback_text)
        return True
    except Exception:
        log.exception("WhatsApp text failed for order %s", order_id)
        return False


def _refund_note(order: dict) -> str:
    # COD is never pre-charged; UPI orders paid upfront are owed the total.
    if order.get("payment_method") == "upi":
        return f"Your UPI payment of ₹{round(float(order.get('total') or 0))} will be refunded."
    return "Nothing was charged, so there is nothing to refund."


def _status_attempts(order: dict, status: str) -> list[tuple]:
    oid, tok = order["id"], _token(order)
    name = order.get("customer_name") or "there"
    pickup = order.get("order_type") == "pickup"
    if status == "preparing":
        return [(T.ORDER_ACCEPTED, _params(name, oid), tok),
                ("order_update_1", _params(name, oid), None)]
    if status == "ready" and pickup:
        return [(T.READY_PICKUP, _params(name, oid, STORE_PICKUP_LINE), tok),
                ("order_pick_up_1", _params(name, oid, STORE_PICKUP_LINE), None)]
    if status == "ready":
        return [(T.READY_DELIVERY, _params(name, oid), tok),
                ("order_confirmed", _params(name, oid), None)]
    if status == "out_for_delivery":
        link = order.get("sr_tracking_url") or _track_url(order)
        return [(T.RIDER_ON_THE_WAY, _params(name, oid, link), tok),
                ("delivery_confirmation_1", _params(name, oid), None)]
    if status == "delivered":
        return [(T.DELIVERED, _params(name, oid), None),
                ("order_delivered", _params(name, oid), None)]
    if status == "cancelled":
        refund = round(float(order.get("total") or 0)) if order.get("payment_method") == "upi" else 0
        return [(T.CANCELLED, _params(name, oid, _refund_note(order)), None),
                ("order_cancelled_1", _params(name, oid, refund), None)]
    return []


def _status_text(order: dict, status: str) -> str | None:
    """Human-readable order status message (used for WhatsApp text + SMS)."""
    oid = order["id"]
    if status == "preparing":
        return f"Order #{oid} is being cooked now. We'll tell you when it leaves the kitchen."
    if status == "ready":
        if order["order_type"] == "pickup":
            return f"Order #{oid} is ready for pickup at {STORE_PICKUP_LINE}."
        return f"Order #{oid} is ready! We're booking your rider now."
    if status == "out_for_delivery":
        track = order.get("sr_tracking_url") or _track_url(order)
        return f"Order #{oid} is on its way! Track the rider: {track}"
    if status == "delivered":
        return (f"Order #{oid} delivered. Enjoy your meal. If anything wasn't right, "
                f"reply here and we'll fix it.")
    if status == "cancelled":
        return f"Order #{oid} has been cancelled. {_refund_note(order)}"
    return None


def notify_status(order: dict, status: str) -> None:
    """Send a status notification to the customer on the available channel."""
    from . import sms

    phone = order.get("customer_phone")
    if not phone:
        return
    try:
        if WHATSAPP_ACTIVE:
            _send_wa(phone, _status_attempts(order, status), _status_text(order, status),
                     order.get("id"))
        else:
            text = _status_text(order, status)
            if text:
                sms.twilio.send_status(phone, text, status=status)
    except Exception:
        log.exception("notify_status failed for order %s", order.get("id"))


def _items_summary(order: dict, limit: int = 60) -> str:
    """'1 North Indian Thali, 2 Masala Chai' cut to fit a template variable."""
    parts = [f"{int(i.get('qty') or 1)} {i.get('name')}" for i in order.get("items") or []]
    out = ""
    for n, p in enumerate(parts):
        nxt = p if not out else f"{out}, {p}"
        if len(nxt) > limit:
            return f"{out} and {len(parts) - n} more" if out else p[:limit]
        out = nxt
    return out or "your food"


def _eta_text(order: dict) -> str:
    if order.get("scheduled_at") or order.get("scheduled_window"):
        from .orders import _window_label
        return _window_label(order.get("scheduled_window"), order.get("scheduled_at"))
    if order.get("order_type") == "pickup":
        return "about 20 minutes for pickup"
    return "about 45 to 60 minutes"


def notify_order_placed(order: dict) -> None:
    """Order confirmation the moment it is placed. WhatsApp only: the
    checkout screen already confirms on the web."""
    phone = order.get("customer_phone")
    if not (WHATSAPP_ACTIVE and phone):
        return
    name = order.get("customer_name") or "there"
    items, eta = _items_summary(order), _eta_text(order)
    total = f"{float(order.get('total') or 0):.2f}".removesuffix(".00")
    attempts = [
        (T.ORDER_PLACED, _params(name, order["id"], items, total, eta), _token(order)),
        # Meta library template, approved instantly, while ours is in review.
        ("order_management_1", _params(name, "order", f"#{order['id']}", items, eta), None),
    ]
    text = (f"Thank you for your order #{order['id']}! We've got {items}. Total ₹{total}. "
            f"Estimated: {eta}. Track it here: {_track_url(order)}")
    try:
        _send_wa(phone, attempts, text, order.get("id"))
    except Exception:
        log.exception("notify_order_placed failed for order %s", order.get("id"))


def notify_delivery_fee(order: dict) -> None:
    """Only for the few orders placed under the old pay-after-booking scheme
    (Oct 7-13 2026): tell the customer the Porter fare they still owe. Free
    text, since its template was retired with that scheme."""
    from . import sms

    phone = order.get("customer_phone")
    fee = order.get("delivery_fee_final")
    if not phone or not fee:
        return
    text = (f"Tulsi Foods: your rider is booked for order #{order['id']}. "
            f"Delivery charge (Porter fare): ₹{float(fee):g}. "
            f"Track and pay it by UPI here: {_track_url(order)}")
    try:
        if WHATSAPP_ACTIVE:
            _send_wa(phone, [], text, order.get("id"))
        else:
            sms.twilio.send_status(phone, text, status="out_for_delivery")
    except Exception:
        log.exception("notify_delivery_fee failed for order %s", order.get("id"))


def notify_dispatch(order: dict, dispatch: dict) -> None:
    """Rider booked / order on its way: the rider's live link plus our
    tracking page button."""
    if order.get("delivery_fee_final"):
        # Old pay-after-booking order: the fare message carries the link.
        notify_delivery_fee(order)
        return
    if dispatch.get("tracking_url") and not order.get("sr_tracking_url"):
        order = {**order, "sr_tracking_url": dispatch["tracking_url"]}
    notify_status(order, "out_for_delivery")
