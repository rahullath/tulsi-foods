"""WhatsApp Cloud API client.

Without credentials it runs in dry-run mode: replies are appended to
WHATSAPP_DRY_LOG so the bot can be developed/tested locally.
"""
import json
import logging
from pathlib import Path

import httpx

from ..config import (
    WHATSAPP_DRY_LOG,
    WHATSAPP_GRAPH_URL,
    WHATSAPP_GRAPH_VERSION,
    WHATSAPP_PHONE_ID,
    WHATSAPP_TOKEN,
)

log = logging.getLogger("whatsapp")


def configured() -> bool:
    return bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)


def _url() -> str:
    return f"{WHATSAPP_GRAPH_URL}/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_ID}/messages"


def _dry_log(payload: dict) -> None:
    try:
        path = Path(WHATSAPP_DRY_LOG)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("dry-run log write failed: %s", e)
    log.info("DRY-RUN WhatsApp message: %s", payload.get("text") or payload.get("interactive"))


def send_text(to: str, body: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    if not configured():
        _dry_log(payload)
        return {"dry_run": True, "to": to, "text": body}
    with httpx.Client(timeout=20) as c:
        r = c.post(_url(), headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, json=payload)
        r.raise_for_status()
        return r.json()


def send_buttons(to: str, body: str, buttons: list[str]) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": [{"type": "reply", "reply": {"id": b, "title": b}} for b in buttons]},
        },
    }
    if not configured():
        _dry_log(payload)
        return {"dry_run": True, "to": to, "text": body}
    with httpx.Client(timeout=20) as c:
        r = c.post(_url(), headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, json=payload)
        r.raise_for_status()
        return r.json()


def send_outbound(to: str, msg: dict) -> dict:
    if msg.get("type") == "buttons":
        return send_buttons(to, msg["text"], msg["buttons"])
    return send_text(to, msg["text"])
