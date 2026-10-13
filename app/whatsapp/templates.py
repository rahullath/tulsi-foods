"""Every WhatsApp template the app sends: name, exact wording, and sync.

One place holds the contract between this app and Meta: the template name,
its body ({{1}}..{{n}} filled by the code), its example values (Meta's review
needs them) and whether it has the "Track order" button, whose URL ends in
the order's tracking token.

`sync()` creates any template that is missing on the WhatsApp Business
Account through the Graph API, so nobody has to type them into WhatsApp
Manager. It runs once at startup and from POST /api/admin/whatsapp/templates/sync.
`check()` compares this list with what Meta has (GET /api/admin/whatsapp/templates).

Rules Meta enforces, all respected below: UTILITY category for transactional
messages, the body must not start or end with a variable, variables need
enough words around them, and no newlines/tabs inside variable values.
"""
import logging
import os
import re

log = logging.getLogger("whatsapp.templates")

LANGUAGE = "en"
TRACK_URL = "https://tulsifoods.app/track/"
TRACK_EXAMPLE = TRACK_URL + "k3x9p2qa"

ORDER_PLACED = "tulsi_order_placed"
ORDER_ACCEPTED = "tulsi_order_accepted"
READY_DELIVERY = "tulsi_order_ready_delivery"
READY_PICKUP = "tulsi_order_ready_pickup"
RIDER_ON_THE_WAY = "tulsi_rider_on_the_way"
DELIVERED = "tulsi_order_delivered"
DELIVERED_RATE = "tulsi_order_delivered_rate"
CANCELLED = "tulsi_order_cancelled"
# KITCHEN_WA_TEMPLATE may override the name, but only with a valid template
# name (Railway once held the template's body text here, which Meta rejects).
_kitchen_env = (os.environ.get("KITCHEN_WA_TEMPLATE") or "").strip()
KITCHEN_ALERT = _kitchen_env if re.fullmatch(r"[a-z0-9_]{1,512}", _kitchen_env) else "tulsi_kitchen_alert"

DEFINITIONS = {
    ORDER_PLACED: {
        "used_for": "customer, the moment the order is placed",
        "body": ("Hi {{1}}, thank you for ordering from Tulsi Foods. Your order #{{2}} "
                 "is with the kitchen: {{3}}. Total ₹{{4}}, estimated time {{5}}. "
                 "We will message you when it is accepted and when it leaves."),
        "example": ["Asha", "142", "1 North Indian Thali, 2 Masala Chai", "367", "about 45 to 60 minutes"],
        "track_button": True,
    },
    ORDER_ACCEPTED: {
        "used_for": "customer, kitchen accepted the order on the POS",
        "body": ("Hi {{1}}, the Tulsi Foods kitchen has accepted your order #{{2}} "
                 "and is cooking it now. We will message you again when it leaves the kitchen."),
        "example": ["Asha", "142"],
        "track_button": True,
    },
    READY_DELIVERY: {
        "used_for": "customer, food ready (delivery order)",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} is packed and ready. "
                 "We are booking your rider now and will send the rider's live tracking link next."),
        "example": ["Asha", "142"],
        "track_button": True,
    },
    READY_PICKUP: {
        "used_for": "customer, food ready (pickup order)",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} is ready for pickup at {{3}}. "
                 "Please show this message at the counter."),
        "example": ["Asha", "142", "34 Murrays Gate Road, Alwarpet"],
        "track_button": True,
    },
    RIDER_ON_THE_WAY: {
        "used_for": "customer, rider booked and on the way",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} is on its way with a Porter rider. "
                 "Follow the rider live here: {{3}} and tap below for your order details."),
        "example": ["Asha", "142", "https://porter.in/track/AB12CD"],
        "track_button": True,
    },
    DELIVERED: {
        "used_for": "customer, order delivered",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} has been delivered. "
                 "If anything was not right, reply to this message and we will fix it."),
        "example": ["Asha", "142"],
        "track_button": False,
    },
    DELIVERED_RATE: {
        "used_for": "customer, order delivered, with a button to rate the dishes",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} has been delivered. "
                 "How was the food? Tap below to rate each dish, it takes ten seconds."),
        "example": ["Asha", "142"],
        "track_button": True,
        "button_text": "Rate your food",
    },
    CANCELLED: {
        "used_for": "customer, order cancelled",
        "body": ("Hi {{1}}, your Tulsi Foods order #{{2}} has been cancelled. {{3}} "
                 "Reply to this message if you have any questions."),
        "example": ["Asha", "142", "Your UPI payment of ₹367 will be refunded within 2 days."],
        "track_button": False,
    },
    KITCHEN_ALERT: {
        "used_for": "kitchen (Mom), Porter booking card and reminders",
        "body": ("Kitchen alert from the Tulsi Foods app: {{1}} "
                 "Reply in this chat with the Porter tracking link and fare once booked."),
        "example": ["Order #142 accepted. PORTER: pickup Tulsi Foods, drop Asha, 12 Luz Church Road, prepaid."],
        "track_button": False,
    },
}

# Kept for the checker's output: what each name expects.
EXPECTED = {name: {"params": d["body"].count("{{"), "url_button": d["track_button"],
                   "used_for": d["used_for"]} for name, d in DEFINITIONS.items()}


def create_payload(name: str) -> dict:
    d = DEFINITIONS[name]
    components = [{"type": "BODY", "text": d["body"], "example": {"body_text": [d["example"]]}}]
    if d["track_button"]:
        components.append({"type": "BUTTONS", "buttons": [{
            "type": "URL", "text": d.get("button_text", "Track order"), "url": TRACK_URL + "{{1}}",
            "example": [TRACK_EXAMPLE]}]})
    return {"name": name, "language": LANGUAGE, "category": "UTILITY", "components": components}


def _shape(components: list[dict]) -> tuple[int, bool]:
    body = next((c for c in components if c.get("type") == "BODY"), {})
    n = body.get("text", "").count("{{")
    url_var = any(
        "{{" in (b.get("url") or "")
        for c in components if c.get("type") == "BUTTONS"
        for b in c.get("buttons", []) if b.get("type") == "URL"
    )
    return n, url_var


def check(meta_templates: list[dict]) -> list[dict]:
    """One row per template the app sends: found?, approved?, and whether
    Meta's variable count matches what the code sends."""
    rows = []
    for name, want in EXPECTED.items():
        found = [t for t in meta_templates if t.get("name") == name]
        approved = [t for t in found if t.get("status") == "APPROVED"]
        row = {"name": name, "used_for": want["used_for"], "code_sends": want["params"],
               "found": bool(found), "approved": bool(approved),
               "languages": sorted({t.get("language") for t in found}),
               "status": sorted({t.get("status") for t in found})}
        if approved:
            n, url_var = _shape(approved[0].get("components", []))
            row["template_has"] = n
            row["url_button_variable"] = url_var
            row["ok"] = n == want["params"] and url_var == want["url_button"]
        else:
            row["ok"] = False
        rows.append(row)
    return rows


_last_sync: dict = {}


def sync() -> dict:
    """Create every template in DEFINITIONS that Meta doesn't have yet.
    Never raises; returns (and remembers) what happened."""
    global _last_sync
    from . import client
    result: dict = {"created": [], "existing": [], "failed": {}}
    try:
        waba = client.waba_id()
        if not waba:
            result["error"] = "WhatsApp Business Account id not found (set WHATSAPP_WABA_ID)"
            return result
        result["waba_id"] = waba
        have = {t.get("name"): t.get("status") for t in client.list_templates(waba)}
        for name in DEFINITIONS:
            if name in have:
                result["existing"].append(f"{name} ({have[name]})")
                continue
            try:
                client.create_template(waba, create_payload(name))
                result["created"].append(name)
            except Exception as e:  # one bad template must not stop the rest
                result["failed"][name] = str(e)[:300]
    except Exception as e:
        result["error"] = str(e)[:300]
    finally:
        _last_sync = result
        log.info("WhatsApp template sync: %s", result)
    return result


def last_sync() -> dict:
    return _last_sync
