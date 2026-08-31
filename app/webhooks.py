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
from .petpooja.config import PETPOOJA_REST_ID, PETPOOJA_WEBHOOK_TOKEN

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
    _relay_rider_status_to_petpooja(order_id, status)


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
    """Send notification on delivery status change (non-fatal).

    Only delivered/cancelled move the customer to act/settle up; intermediate
    webhook statuses are handled by the dispatch flow, so skip them here.
    """
    if status not in ("delivered", "cancelled"):
        return
    from .notify import notify_status
    notify_status(order, status)


# ---- Borzo -> Petpooja rider status relay ----
# Piggybacks on the existing Borzo webhook: whenever our courier's status
# changes and this order was pushed to Petpooja POS, tell Petpooja too (their
# "Rider Information" webhook), so the kitchen terminal shows live courier
# status instead of just "dispatched". Best-effort — never blocks the primary
# Borzo status handling above.
_BORZO_TO_PETPOOJA_RIDER_STATUS = {
    "courier_assigned": "rider-assigned",
    "courier_arrived": "rider-arrived",
    "courier_at_pickup": "rider-arrived",
    "parcel_picked_up": "pickedup",
    "finished": "delivered",
}


def _relay_rider_status_to_petpooja(order_id: int, borzo_status: str) -> None:
    mapped = _BORZO_TO_PETPOOJA_RIDER_STATUS.get(borzo_status)
    if not mapped:
        return
    try:
        from . import db
        from .petpooja.client import is_configured, push_rider_status
        if not is_configured():
            return
        o = db.get_order(order_id)
        if not o or not o.get("petpooja_order_id"):
            return
        push_rider_status(order_id, mapped)
    except Exception:
        log.exception("Petpooja rider status relay failed for order %s", order_id)


# ---- Petpooja POS webhooks ----
# Endpoints Petpooja calls (we host these, per the "Push Menu" / "Order
# Callback" / stock+store status API docs). Petpooja's docs don't specify a
# request-signing scheme for these, so we hand Petpooja these URLs with our
# own shared-secret token baked in as ?t=... — verified below.

def _check_petpooja_token(t: str | None) -> None:
    if PETPOOJA_WEBHOOK_TOKEN and t != PETPOOJA_WEBHOOK_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


@router.post("/petpooja/order-callback")
async def petpooja_order_callback(request: Request, t: str | None = Query(None)):
    """Petpooja POS -> us: order status changed (accepted/dispatch/ready/delivered/cancelled)."""
    _check_petpooja_token(t)
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from . import db
    from .petpooja.mapping import petpooja_status_to_order_status

    order_id_raw = body.get("orderID")
    status_code = body.get("status")
    if not order_id_raw or status_code is None:
        return {"success": "0", "message": "Missing orderID or status"}

    mapped = petpooja_status_to_order_status(status_code)
    if not mapped:
        log.info("Petpooja callback: unrecognised status %s for order %s", status_code, order_id_raw)
        return {"success": "1", "message": "Ignored (unrecognised status)"}

    try:
        order_id = int(order_id_raw)
    except (TypeError, ValueError):
        return {"success": "0", "message": "Invalid orderID"}

    o = db.get_order(order_id)
    if not o:
        return {"success": "0", "message": "Order not found"}
    if o["status"] in ("delivered", "cancelled"):
        return {"success": "1", "message": "No-op (order already closed)"}

    db.update_order_status(order_id, mapped)
    log.info("Order %s: %s -> %s (Petpooja callback: %s)", order_id, o["status"], mapped, status_code)
    _send_status_whatsapp_if_needed(db.get_order(order_id), mapped)
    return {"success": "1", "message": "Status updated"}


@router.post("/petpooja/menu")
async def petpooja_push_menu(request: Request, t: str | None = Query(None)):
    """Petpooja POS -> us: menu changed. Cached only for now — NOT wired into
    the live customer-facing menu (data/menu.json stays the source until the
    item-id reconciliation described in app/petpooja/mapping.py is done and
    someone deliberately flips the switch)."""
    _check_petpooja_token(t)
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from .config import DATA_DIR
    cache_file = DATA_DIR / "petpooja_menu_raw.json"
    try:
        cache_file.write_text(json.dumps(body, indent=2), encoding="utf-8")
        log.info("Petpooja push-menu received and cached (%d bytes)", len(json.dumps(body)))
    except Exception:
        log.exception("Failed to cache Petpooja pushed menu")

    return {"success": True, "message": "Menu received"}


@router.post("/petpooja/stock")
async def petpooja_update_stock(request: Request, t: str | None = Query(None)):
    """Petpooja POS -> us: item/addon marked in/out of stock. Logged only for
    now — see the item-id note in app/petpooja/mapping.py for why this isn't
    wired into app.db.set_availability() yet."""
    _check_petpooja_token(t)
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    log.info("Petpooja stock toggle: %s", body)
    return {"code": "200", "status": "success", "message": "Received"}


@router.api_route("/petpooja/store-status", methods=["GET", "POST"])
async def petpooja_get_store_status(t: str | None = Query(None)):
    """Petpooja POS -> us: 'is the store open for online orders'."""
    _check_petpooja_token(t)
    from . import db
    status = db.get_store_status()
    return {
        "restID": PETPOOJA_REST_ID,
        "status": "success",
        "store_status": "1" if status["is_open"] else "0",
        "http_code": "200",
        "message": "OK",
    }


@router.post("/petpooja/store-status/update")
async def petpooja_update_store_status(request: Request, t: str | None = Query(None)):
    """Petpooja POS -> us: merchant flipped store open/closed on the POS terminal.
    Gates new order creation — see the store-status check in app/orders.py."""
    _check_petpooja_token(t)
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from . import db
    is_open = str(body.get("store_status")) == "1"
    db.set_store_status(is_open, reason=body.get("reason"), turn_on_time=body.get("turn_on_time"))
    log.info("Store status set to %s (reason: %s)", "open" if is_open else "closed", body.get("reason"))
    return {
        "http_code": 200,
        "status": "success",
        "message": f"Store Status updated successfully for store {body.get('restID', PETPOOJA_REST_ID)}",
    }
