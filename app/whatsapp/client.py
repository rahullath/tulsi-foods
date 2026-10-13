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


def wa_number(to: str) -> str:
    """Cloud API wants the full international number without '+'. Customer
    phones are stored as bare 10-digit Indian numbers, which Meta reads as a
    different country (or rejects), so add 91 to anything 10 digits long."""
    digits = "".join(ch for ch in str(to or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return "91" + digits if len(digits) == 10 else digits


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
        "to": wa_number(to),
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
        "to": wa_number(to),
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


def send_list(to: str, body: str, button: str, sections: list[dict]) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": wa_number(to),
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button,
                "sections": sections,
            },
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
    if msg.get("type") == "list":
        return send_list(to, msg["text"], msg["button"], msg["sections"])
    if msg.get("type") == "template":
        return send_template(to, msg["name"], msg.get("language", "en"), msg.get("params", []))
    return send_text(to, msg["text"])


class WhatsAppError(Exception):
    """A Graph API refusal, with Meta's error code (e.g. 132001 = template
    not found in that language, 132000 = wrong number of parameters)."""

    def __init__(self, status: int, code, message: str):
        self.status, self.code = status, code
        super().__init__(f"WhatsApp {status} (code {code}): {message}")


# Library templates added in WhatsApp Manager default to "English (US)" =
# en_US, which Meta treats as a different template from "en". Try the asked
# language first, then the other English variants, and remember what worked.
_ENGLISH = ("en_US", "en", "en_GB")
_lang_that_worked: dict[str, str] = {}


def _post(payload: dict) -> dict:
    with httpx.Client(timeout=20) as c:
        r = c.post(_url(), headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, json=payload)
    if r.is_success:
        return r.json()
    try:
        err = r.json().get("error", {})
    except ValueError:
        err = {}
    raise WhatsAppError(r.status_code, err.get("code"), err.get("message") or r.text[:200])


def send_template(to: str, name: str, language: str = "en",
                  params: list[dict] | None = None,
                  button_url_suffix: str | None = None) -> dict:
    """Send a pre-approved template message.

    Each param is {"type": "text", "text": "value"}. `button_url_suffix`
    fills a dynamic URL button ({{1}} at the end of the button's URL).
    """
    components = []
    if params:
        components.append({"type": "body", "parameters": params})
    if button_url_suffix:
        components.append({"type": "button", "sub_type": "url", "index": "0",
                           "parameters": [{"type": "text", "text": button_url_suffix}]})
    langs = [_lang_that_worked.get(name, language)]
    langs += [l for l in (language, *_ENGLISH) if l not in langs]
    last_err = None
    for lang in langs:
        template: dict = {"name": name, "language": {"code": lang}}
        if components:
            template["components"] = components
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": wa_number(to),
            "type": "template",
            "template": template,
        }
        if not configured():
            _dry_log(payload)
            return {"dry_run": True, "to": to, "template": name}
        try:
            result = _post(payload)
            _lang_that_worked[name] = lang
            return result
        except WhatsAppError as e:
            last_err = e
            if e.code != 132001:  # only "not found in this language" is worth retrying
                break
    log.warning("template %s failed: %s", name, last_err)
    raise last_err


def list_templates(waba_id: str) -> list[dict]:
    """Every message template on the WhatsApp Business Account, as Meta has
    them (name, status, language, category, components)."""
    url = f"{WHATSAPP_GRAPH_URL}/{WHATSAPP_GRAPH_VERSION}/{waba_id}/message_templates"
    out, params = [], {"fields": "name,status,language,category,components", "limit": 200}
    with httpx.Client(timeout=20) as c:
        while url:
            r = c.get(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, params=params)
            r.raise_for_status()
            data = r.json()
            out += data.get("data", [])
            url, params = data.get("paging", {}).get("next"), None
    return out


_waba_cache: list[str] = []


def waba_id() -> str:
    """The WhatsApp Business Account that owns WHATSAPP_PHONE_ID:
    WHATSAPP_WABA_ID if set, else looked up among the business portfolio's
    WABAs (a system-user token's debug_token carries no WABA id), so
    switching to another phone number needs no extra variable."""
    from ..config import META_BUSINESS_ID, WHATSAPP_WABA_ID
    if WHATSAPP_WABA_ID:
        return WHATSAPP_WABA_ID
    if _waba_cache:
        return _waba_cache[0]
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID and META_BUSINESS_ID):
        return ""
    base = f"{WHATSAPP_GRAPH_URL}/{WHATSAPP_GRAPH_VERSION}"
    auth = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    with httpx.Client(timeout=20) as c:
        for edge in ("owned_whatsapp_business_accounts", "client_whatsapp_business_accounts"):
            r = c.get(f"{base}/{META_BUSINESS_ID}/{edge}", headers=auth, params={"fields": "id"})
            if not r.is_success:
                continue
            for waba in r.json().get("data", []):
                p = c.get(f"{base}/{waba['id']}/phone_numbers", headers=auth, params={"fields": "id"})
                if p.is_success and any(n.get("id") == WHATSAPP_PHONE_ID for n in p.json().get("data", [])):
                    _waba_cache.append(str(waba["id"]))
                    return _waba_cache[0]
    return ""


def create_template(waba: str, payload: dict) -> dict:
    """Submit a message template for Meta's review (UTILITY ones are usually
    approved within minutes)."""
    url = f"{WHATSAPP_GRAPH_URL}/{WHATSAPP_GRAPH_VERSION}/{waba}/message_templates"
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, json=payload)
    if r.is_success:
        return r.json()
    try:
        err = r.json().get("error", {})
    except ValueError:
        err = {}
    raise WhatsAppError(r.status_code, err.get("code"),
                        err.get("error_user_msg") or err.get("message") or r.text[:200])
