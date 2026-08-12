"""WhatsApp Cloud API webhook endpoints.

GET  /webhook/whatsapp  — Meta's verification handshake.
POST /webhook/whatsapp  — inbound messages + status events.
"""
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from .config import WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN
from .whatsapp import client, conversation

log = logging.getLogger("webhook")
router = APIRouter(prefix="/webhook", tags=["webhook"])


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


def _extract_messages(body: dict) -> list[dict]:
    out = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                m = msg.get("text", {}).get("body")
                if msg.get("type") == "interactive":
                    intr = msg.get("interactive", {})
                    if intr.get("type") == "button_reply":
                        m = intr.get("button_reply", {}).get("id")
                    elif intr.get("type") == "list_reply":
                        m = intr.get("list_reply", {}).get("id")
                if m is None:
                    continue
                profile_name = ""
                for contact in value.get("contacts", []):
                    profile_name = contact.get("profile", {}).get("name", "")
                out.append({
                    "wa_id": msg.get("from", ""),
                    "text": str(m),
                    "profile_name": profile_name,
                })
    return out


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
    for msg in _extract_messages(body):
        try:
            replies = conversation.handle(msg["wa_id"], msg["text"], msg["profile_name"])
            for reply in replies:
                client.send_outbound(msg["wa_id"], reply)
        except Exception:
            log.exception("failed to process message from %s", msg["wa_id"])
    return {"status": "ok"}
