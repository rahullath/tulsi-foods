"""WhatsApp Cloud API + Borzo delivery webhook endpoints.

GET  /webhook/whatsapp  — Meta's verification handshake.
POST /webhook/whatsapp  — inbound messages + status events.
POST /webhook/borzo     — Borzo delivery status updates.
"""
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from .config import WHATSAPP_APP_SECRET, WHATSAPP_PHONE_ID, WHATSAPP_VERIFY_TOKEN, ADMIN_PHONE
from .whatsapp import client, conversation, sessions

log = logging.getLogger("webhook")
router = APIRouter(prefix="/webhook", tags=["webhook"])


def _echo_customers(body: dict) -> list[str]:
    """Customer numbers whose chats the business answered from the WhatsApp
    Business app (Coexistence `smb_message_echoes` webhook). Once a human has
    replied to a chat, the bot stays out of it."""
    customers = set()
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for thread in value.get("smb_message_echoes", []):
                tid = thread.get("id")
                for msg in thread.get("messages", []):
                    cust = msg.get("to") or tid or msg.get("from")
                    if cust and cust != WHATSAPP_PHONE_ID:
                        customers.add(str(cust))
    return list(customers)


def _extract_messages(body: dict) -> list[dict]:
    out = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("from") == WHATSAPP_PHONE_ID:
                    continue  # echo of a message WE sent / mom's app reply — never self-reply
                m = msg.get("text", {}).get("body")
                lat = None
                lng = None
                if msg.get("type") == "interactive":
                    intr = msg.get("interactive", {})
                    if intr.get("type") == "button_reply":
                        m = intr.get("button_reply", {}).get("id")
                    elif intr.get("type") == "list_reply":
                        m = intr.get("list_reply", {}).get("id")
                elif msg.get("type") == "location":
                    loc = msg.get("location", {})
                    lat = str(loc.get("latitude", ""))
                    lng = str(loc.get("longitude", ""))
                    m = f"[Location: {lat}, {lng}]"
                if m is None:
                    continue
                profile_name = ""
                for contact in value.get("contacts", []):
                    profile_name = contact.get("profile", {}).get("name", "")
                out.append({
                    "wa_id": msg.get("from", ""),
                    "text": str(m),
                    "profile_name": profile_name,
                    "lat": lat,
                    "lng": lng,
                })
    return out


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not WHATSAPP_APP_SECRET:
        return True
    if not signature:
        return False
    expected = hmac.new(WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + expected, signature)


@router.get("/whatsapp")
def verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge or "")
    return PlainTextResponse("Verification failed", status_code=403)


@router.post("/whatsapp")
async def inbound(request: Request, x_hub_signature_256: str | None = Header(None)):
    raw = await request.body()
    if not _verify_signature(raw, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    log.debug("webhook payload: %s", body)
    for cust in _echo_customers(body):
        sessions.set_human(cust, True)
        log.info("human took over chat for %s", cust)
    for msg in _extract_messages(body):
        if sessions.is_human(msg["wa_id"]):
            log.info("bot paused for %s (human-owned)", msg["wa_id"])
            continue
        # Check if this is an admin command from mom's phone
        if ADMIN_PHONE and msg["wa_id"] == ADMIN_PHONE:
            from .whatsapp.admin_commands import is_admin_command, handle_admin_command
            if is_admin_command(msg["text"]):
                reply_text = handle_admin_command(msg["text"])
                client.send_text(msg["wa_id"], reply_text)
                log.info("admin command from %s: %s → %s", msg["wa_id"], msg["text"], reply_text)
                continue
        try:
            replies = conversation.handle(msg["wa_id"], msg["text"], msg["profile_name"],
                                            lat=msg.get("lat"), lng=msg.get("lng"))
            for reply in replies:
                client.send_outbound(msg["wa_id"], reply)
        except Exception:
            log.exception("failed to process message from %s", msg["wa_id"])
    return {"status": "ok"}


# ---- Borzo delivery status webhook ----

@router.post("/borzo")
async def borzo_webhook(request: Request, x_dv_signature: str | None = Header(None)):
    """Borzo sends status updates when orders/deliveries change."""
    raw = await request.body()
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Verify signature if callback token is set
    from .delivery.config import BORZO_CALLBACK_TOKEN
    if BORZO_CALLBACK_TOKEN and x_dv_signature:
        expected = hmac.new(BORZO_CALLBACK_TOKEN.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_dv_signature):
            log.warning("Borzo webhook: invalid signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    event_type = body.get("event_type", "")
    log.info("Borzo webhook: %s", event_type)

    # Handle delivery status changes
    if event_type in ("delivery_changed", "delivery_created"):
        delivery = body.get("delivery", {})
        status = delivery.get("status", "")
        order_id = delivery.get("client_order_id")  # our internal order ID
        if order_id:
            _handle_borzo_delivery_status(int(order_id), status, delivery)

    # Handle order status changes
    elif event_type in ("order_changed", "order_created"):
        order = body.get("order", {})
        status = order.get("status", "")
        # Find our order ID from the points
        for point in order.get("points", []):
            cid = point.get("client_order_id")
            if cid:
                _handle_borzo_order_status(int(cid), status, order)
                break

    return {"status": "ok"}


# Borzo delivery status → our order status
_BORZO_DELIVERY_STATUS_MAP = {
    "courier_assigned": "out_for_delivery",
    "courier_departed": "out_for_delivery",
    "courier_at_pickup": "out_for_delivery",
    "parcel_picked_up": "out_for_delivery",
    "courier_arrived": "out_for_delivery",
    "finished": "delivered",
    "canceled": "cancelled",
    "return_planned": "cancelled",
    "return_finished": "cancelled",
}

_BORZO_ORDER_STATUS_MAP = {
    "new": "ready",
    "available": "ready",
    "active": "out_for_delivery",
    "completed": "delivered",
    "canceled": "cancelled",
}


def _handle_borzo_delivery_status(order_id: int, status: str, delivery: dict) -> None:
    """Update order status based on Borzo delivery webhook."""
    from . import db
    mapped = _BORZO_DELIVERY_STATUS_MAP.get(status)
    if not mapped:
        log.info("Borzo delivery status '%s' for order %s — no action", status, order_id)
        return
    o = db.get_order(order_id)
    if not o:
        log.warning("Borzo webhook: order %s not found", order_id)
        return
    # Only advance, never regress
    current = o["status"]
    if current == "delivered" or current == "cancelled":
        return
    db.update_order_status(order_id, mapped)
    log.info("Order %s: %s → %s (Borzo delivery: %s)", order_id, current, mapped, status)
    _send_status_whatsapp_if_needed(o, mapped)


def _handle_borzo_order_status(order_id: int, status: str, order: dict) -> None:
    """Update order status based on Borzo order webhook."""
    from . import db
    mapped = _BORZO_ORDER_STATUS_MAP.get(status)
    if not mapped:
        return
    o = db.get_order(order_id)
    if not o:
        return
    current = o["status"]
    if current == "delivered" or current == "cancelled":
        return
    db.update_order_status(order_id, mapped)
    log.info("Order %s: %s → %s (Borzo order: %s)", order_id, current, mapped, status)
    _send_status_whatsapp_if_needed(o, mapped)


def _send_status_whatsapp_if_needed(order: dict, status: str) -> None:
    """Send WhatsApp notification on delivery status change (non-fatal)."""
    try:
        phone = order.get("customer_phone", "")
        if not phone:
            return
        oid = order["id"]
        if status == "delivered":
            msg = (
                f"Order #{oid} delivered! Enjoy your meal 🙏 If anything wasn't right, reply here and we'll fix it.\n\n"
                f"If you did enjoy it, an honest Google review helps our small kitchen a lot."
            )
        elif status == "cancelled":
            msg = f"Order #{oid} has been cancelled."
        else:
            return  # don't spam for intermediate statuses
        client.send_text(phone, msg)
    except Exception:
        pass  # non-fatal
