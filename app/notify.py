"""Customer notification dispatch — WhatsApp primary, SMS (Twilio) fallback.

Order: if WHATSAPP_ACTIVE is set (Meta verified), send via WhatsApp (trying the
pre-approved template first, then plain text). Otherwise fall back to SMS via
Twilio. This keeps customers notified even while Meta verification is pending —
see docs/META_CONTINGENCY_PLAN.md §7.
"""
import logging

from .config import WHATSAPP_ACTIVE

log = logging.getLogger("notify")


def _status_template(order: dict, status: str):
    """Return the (template_name, params) for a status, or None."""
    oid = order["id"]
    cname = order.get("customer_name") or "there"
    t = lambda *params: [{"type": "text", "text": str(p)} for p in params]
    templates = {
        "preparing": ("order_update_1", t(cname, oid)),
    }
    if order["order_type"] == "pickup":
        templates["ready"] = (
            "order_pick_up_1",
            t(cname, oid, order.get("delivery_address") or "Tulsi Foods, Alwarpet"),
        )
    else:
        templates["ready"] = ("order_confirmed", t(cname, oid))
    templates["delivered"] = ("order_delivered", t(cname, oid))
    # COD is never pre-charged, so there's nothing to refund; UPI orders are
    # paid upfront, so a cancellation owes back the actual order total.
    refund = order["total"] if order.get("payment_method") == "upi" else 0
    templates["cancelled"] = ("order_cancelled_1", t(cname, oid, round(refund)))
    templates["out_for_delivery"] = ("delivery_confirmation_1", t(cname, oid))
    return templates.get(status)


def _status_text(order: dict, status: str) -> str | None:
    """Human-readable order status message (used for WhatsApp text + SMS)."""
    oid = order["id"]
    if status == "preparing":
        return f"Order #{oid} is being cooked now. We'll tell you when it leaves the kitchen."
    if status == "ready":
        if order["order_type"] == "pickup":
            return f"Order #{oid} is ready for pickup! Come and collect."
        return f"Order #{oid} is ready! Dispatching shortly."
    if status == "out_for_delivery":
        track = order.get("sr_tracking_url") or "we will update you"
        return f"Order #{oid} is on its way! Track: {track}."
    if status == "delivered":
        return (
            f"Order #{oid} delivered. Enjoy your meal. If anything wasn't right, "
            f"reply here and we'll fix it."
        )
    if status == "cancelled":
        return f"Order #{oid} has been cancelled."
    return None


def notify_status(order: dict, status: str) -> None:
    """Send a status notification to the customer on the available channel."""
    from . import sms, whatsapp  # lazy to avoid import cycles

    phone = order.get("customer_phone")
    if not phone:
        return
    try:
        if WHATSAPP_ACTIVE:
            tpl = _status_template(order, status)
            if tpl:
                name, params = tpl
                try:
                    whatsapp.client.send_template(phone, name, "en", params)
                    return
                except Exception:
                    pass  # template not approved → fall back to text
            text = _status_text(order, status)
            if text:
                whatsapp.client.send_text(phone, text)
                return
        else:
            text = _status_text(order, status)
            if text:
                sms.twilio.send_status(phone, text, status=status)
                return
    except Exception:
        log.exception("notify_status failed for order %s", order.get("id"))


def _track_url(order: dict) -> str:
    return f"https://tulsifoods.app/track/{order.get('tracking_token') or order['id']}"


# WhatsApp templates for delivery messages. Create each in WhatsApp Manager
# as category UTILITY, language "en", with exactly these numbered variables
# (docs/WHATSAPP_TEMPLATES.md has the body text to paste):
#   delivery_fare     {{1}} name, {{2}} order no., {{3}} fare, {{4}} track link
#   rider_on_the_way  {{1}} name, {{2}} order no., {{3}} track link
TPL_DELIVERY_FARE = "delivery_fare"
TPL_RIDER_ON_THE_WAY = "rider_on_the_way"


def _params(*values) -> list[dict]:
    return [{"type": "text", "text": str(v)} for v in values]


def _send_wa(phone: str, template: str, params: list[dict], fallback_text: str,
             order_id) -> bool:
    """Template first (the only thing Meta delivers outside the 24 h window),
    then free text (delivered only if the customer wrote to us in the last
    24 h). Returns True if WhatsApp accepted either."""
    from . import whatsapp
    try:
        whatsapp.client.send_template(phone, template, "en", params)
        return True
    except Exception:
        log.warning("template %s failed for order %s (not approved yet?); trying text",
                    template, order_id)
    try:
        whatsapp.client.send_text(phone, fallback_text)
        return True
    except Exception:
        log.exception("WhatsApp text failed for order %s", order_id)
        return False


def notify_delivery_fee(order: dict) -> None:
    """The real delivery charge once the rider is booked, with the tracking
    page link (which carries the UPI pay button). WhatsApp template; SMS only
    when WhatsApp is off, since unregistered (non-DLT) SMS is dropped."""
    from . import sms

    phone = order.get("customer_phone")
    fee = order.get("delivery_fee_final")
    if not phone or not fee:
        return
    name = order.get("customer_name") or "there"
    fare = f"{float(fee):g}"
    text = (f"Tulsi Foods: your rider is booked for order #{order['id']}. "
            f"Delivery charge (Porter fare): ₹{fare}. "
            f"Track and pay it by UPI here: {_track_url(order)}")
    try:
        if WHATSAPP_ACTIVE:
            _send_wa(phone, TPL_DELIVERY_FARE, _params(name, order["id"], fare, _track_url(order)),
                     text, order.get("id"))
        else:
            sms.twilio.send_status(phone, text, status="out_for_delivery")
    except Exception:
        log.exception("notify_delivery_fee failed for order %s", order.get("id"))


def notify_dispatch(order: dict, dispatch: dict) -> None:
    """Rider booked / order on its way. One message: the fare template when
    the fare is known (it carries the link too), else rider_on_the_way."""
    from . import sms

    phone = order.get("customer_phone")
    if not phone:
        return
    if order.get("delivery_fee_final"):
        notify_delivery_fee(order)
        return
    name = order.get("customer_name") or "there"
    text = f"Order #{order['id']} is on its way! Track it here: {_track_url(order)}"
    try:
        if WHATSAPP_ACTIVE:
            _send_wa(phone, TPL_RIDER_ON_THE_WAY, _params(name, order["id"], _track_url(order)),
                     text, order.get("id"))
        else:
            sms.twilio.send_status(phone, text, status="out_for_delivery")
    except Exception:
        log.exception("notify_dispatch failed for order %s", order.get("id"))
