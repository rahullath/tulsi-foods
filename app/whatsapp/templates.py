"""Every WhatsApp template the code sends, and what it expects of each.

One place to see the contract between this app and WhatsApp Manager: the
template name, how many body variables the code fills ({{1}}..{{n}}) and
whether it fills a dynamic URL button. `check()` compares this list with the
templates Meta actually has (GET /api/admin/whatsapp/templates), so a missing,
unapproved or mismatched template shows up before a customer misses a message.
"""
import os

EXPECTED = {
    os.environ.get("ORDER_PLACED_TEMPLATE", "order_management_1"): {
        "params": 5, "url_button": False,
        "used_for": "order placed (customer): name, 'order', order no., items, estimated time"},
    "order_update_1": {"params": 2, "url_button": False,
                       "used_for": "POS accepted the order: name, order no."},
    "order_confirmed": {"params": 2, "url_button": False,
                        "used_for": "food ready, delivery order: name, order no."},
    "order_pick_up_1": {"params": 3, "url_button": False,
                        "used_for": "food ready, pickup order: name, order no., pickup address"},
    "delivery_confirmation_1": {"params": 2, "url_button": False,
                                "used_for": "POS marked it dispatched: name, order no."},
    "order_delivered": {"params": 2, "url_button": False,
                        "used_for": "delivered: name, order no."},
    "order_cancelled_1": {"params": 3, "url_button": False,
                          "used_for": "cancelled: name, order no., refund amount"},
    "rider_on_the_way": {"params": 3, "url_button": False,
                         "used_for": "rider booked, fare not known yet: name, order no., track link"},
    "delivery_fare": {"params": 4, "url_button": False,
                      "used_for": "rider booked with fare: name, order no., fare, track link"},
    os.environ.get("KITCHEN_WA_TEMPLATE", "kitchen_alert"): {
        "params": 1, "url_button": False, "used_for": "Porter booking card to the kitchen"},
}


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
    """One row per expected template: found?, approved?, languages, and
    whether Meta's variable count matches what the code sends."""
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
