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
    templates["cancelled"] = ("order_cancelled_1", t(cname, oid, "0"))
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


def notify_dispatch(order: dict, dispatch: dict) -> None:
    """Notify the customer that their order has been dispatched/assigned."""
    from . import sms, whatsapp

    phone = order.get("customer_phone")
    if not phone:
        return
    try:
        if WHATSAPP_ACTIVE:
            try:
                params = [
                    {"type": "text", "text": str(order.get("customer_name") or "there")},
                    {"type": "text", "text": str(order["id"])},
                ]
                whatsapp.client.send_template(phone, "order_shipped", "en", params)
                return
            except Exception:
                pass
            whatsapp.client.send_text(
                phone,
                f"Your order #{order['id']} is on its way!\n"
                f"Courier: {dispatch.get('courier_name')}\n"
                f"Track: {dispatch.get('tracking_url')}\n",
            )
            return
        else:
            sms.twilio.send_status(
                phone,
                f"Order #{order['id']} is on its way! "
                f"Track: {dispatch.get('tracking_url')}\n",
                status="out_for_delivery",
            )
            return
    except Exception:
        log.exception("notify_dispatch failed for order %s", order.get("id"))
