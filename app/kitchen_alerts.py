"""Kitchen alerts: messages to Mom's phone, driven by the POS.

Channel: WhatsApp from the business number to ADMIN_PHONE (Mom's personal
number, wa_id form e.g. "9198XXXXXXXX"), with Telegram as a second channel
when configured. Meta only allows free-form text inside 24 h of Mom's last
message to the business number; outside that window it must be an approved
template. Set KITCHEN_WA_TEMPLATE to a UTILITY template with ONE body
variable (see docs/COURIER_ROUTER.md) and alerts always get through.

The Porter loop this powers:
  POS Accept      -> Porter booking card to Mom
  POS Food Ready  -> reminder if no rider recorded yet
  Mom forwards the Porter tracking link to the business WhatsApp
                  -> handle_admin_tracking_link() records it, notifies customer
"""
import logging
import os
import re

from .config import ADMIN_PHONE, WHATSAPP_ACTIVE

log = logging.getLogger("kitchen")

KITCHEN_WA_TEMPLATE = os.environ.get("KITCHEN_WA_TEMPLATE", "")
KITCHEN_WA_TEMPLATE_LANG = os.environ.get("KITCHEN_WA_TEMPLATE_LANG", "en")


def _template_safe(text: str) -> str:
    # Template variables may not contain newlines, tabs or 4+ spaces in a row.
    return re.sub(r"\s{2,}", " ", text.replace("\n", " | ")).strip()[:1000]


def send(text: str, html_text: str | None = None) -> list[str]:
    """Send `text` to the kitchen on every configured channel; returns the
    channels that accepted it. Never raises."""
    sent = []
    if WHATSAPP_ACTIVE and ADMIN_PHONE:
        from .whatsapp import client
        try:
            if KITCHEN_WA_TEMPLATE:
                client.send_template(ADMIN_PHONE, KITCHEN_WA_TEMPLATE, KITCHEN_WA_TEMPLATE_LANG,
                                     [{"type": "text", "text": _template_safe(text)}])
            else:
                client.send_text(ADMIN_PHONE, text)
            sent.append("whatsapp")
        except Exception:
            log.exception("kitchen WhatsApp alert failed (template=%s)", KITCHEN_WA_TEMPLATE or "-")
    from . import telegram
    if telegram.enabled():
        from html import escape
        if telegram.send_message(html_text or escape(text)):
            sent.append("telegram")
    if not sent:
        log.warning("kitchen alert not delivered on any channel: %s", text[:120])
    return sent


def porter_card(order: dict, reason: str) -> list[str]:
    """Send the Porter booking card for a delivery order."""
    from html import escape
    from .delivery import porter
    card = porter.booking_text(order)
    tail = ("\n\nBooked? Send the Porter tracking link AND the fare here, "
            f"e.g. \"<link> ₹86\" (add #{order['id']} if more than one order is waiting).")
    return send(f"{reason}\n\n{card}{tail}",
                f"{escape(reason)}\n\n<pre>{escape(card)}</pre>{escape(tail)}")


_URL = re.compile(r"https?://\S+")
_FARE = re.compile(r"(?:₹|\brs\.?|\binr|\bfare)\s*:?\s*(\d{2,4}(?:\.\d{1,2})?)", re.I)
_ORDER_REF = re.compile(r"#\s*(\d{1,7})\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")


def looks_like_tracking_link(text: str) -> bool:
    """A courier link and/or a fare ("₹86", "Rs 86", "fare 86") from Mom."""
    return bool(_URL.search(text or "") or _FARE.search(text or ""))


def _fare(text: str) -> float | None:
    m = _FARE.search(_URL.sub(" ", text or ""))
    return float(m.group(1)) if m else None


def handle_admin_tracking_link(text: str) -> str:
    """Mom sent a courier link and/or the fare: attach it to the right order.

    Link (+ optional fare): the waiting delivery order (preparing/ready, no
    rider yet) — "#<id>" picks one when several wait. Fare alone: the order
    that has a rider but no fare yet. Returns the reply for Mom."""
    from . import db, orders
    m_url = _URL.search(text)
    url = m_url.group(0).rstrip(").,") if m_url else ""
    fare = _fare(text)
    ref = _ORDER_REF.search(text)
    today = [o for o in db.today_orders() if o.get("order_type") == "delivery"]
    if url:
        pool = [o for o in today if o.get("status") in ("preparing", "ready")
                and not (o.get("sr_courier") or o.get("sr_tracking_url"))]
        none_msg = "No delivery order is waiting for a rider right now."
    else:
        pool = [o for o in today if (o.get("sr_courier") or o.get("sr_tracking_url"))
                and not o.get("delivery_fee_final") and o.get("status") != "cancelled"]
        none_msg = "No booked order is waiting for its fare. Send the Porter link with the fare."
    if ref:
        target = next((o for o in pool if o["id"] == int(ref.group(1))), None)
        if not target:
            return f"Order #{ref.group(1)} isn't waiting for that (already done, or not a delivery)."
    elif len(pool) == 1:
        target = pool[0]
    elif not pool:
        return none_msg
    else:
        ids = ", ".join(f"#{o['id']}" for o in pool)
        return f"Which order is this for? Waiting: {ids}. Send it again with the number, e.g. #{pool[0]['id']}."

    from .notify import notify_dispatch, notify_delivery_fee
    try:
        if url:
            phone = _PHONE.search(_URL.sub(" ", text))
            result = orders.record_manual_dispatch(
                target["id"], url, "", re.sub(r"\D", "", phone.group(1)) if phone else "", fare)
        else:
            orders.record_delivery_fee(target["id"], fare)
    except orders.OrderError as e:
        return f"Couldn't save it: {e.message}"
    try:
        o = db.get_order(target["id"])
        if url:
            notify_dispatch(o, result)
        elif fare:
            notify_delivery_fee(o)
    except Exception:
        log.exception("customer notification failed for order %s", target["id"])
    if url and not fare:
        return (f"✅ Order #{target['id']} is out for delivery. What did Porter charge? "
                f"Reply e.g. \"#{target['id']} ₹86\" so the customer can pay it.")
    if url:
        return f"✅ Order #{target['id']} is out for delivery. Customer has the link and the ₹{fare:g} delivery charge."
    return f"✅ Delivery ₹{fare:g} saved for order #{target['id']}. The customer has been asked to pay it."
