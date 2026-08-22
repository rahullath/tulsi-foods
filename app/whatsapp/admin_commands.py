"""WhatsApp commands for mom to manage the menu from her phone.

Parse natural-language commands:
  "dal sold out"          → mark item unavailable
  "chola bhatura back"    → mark item available
  "special mango lassi 89" → set today's special
  "all on"                → mark everything available
"""
import re
from datetime import date

from .. import db, menu


def is_admin_command(text: str) -> bool:
    t = text.strip().lower()
    return any([
        "sold out" in t,
        t.endswith(" back"),
        t.startswith("special "),
        t in ("all on", "all available", "everything on"),
    ])


def handle_admin_command(text: str) -> str:
    t = text.strip().lower()
    today = date.today().isoformat()

    # "all on" / "all available"
    if t in ("all on", "all available", "everything on"):
        all_ids = [m["id"] for m in menu.load_menu()]
        db.set_availability(today, all_ids, [])
        return f"All {len(all_ids)} items set to available."

    # "special mango lassi 89"
    m_special = re.match(r"^special\s+(.+?)\s+(\d+(?:\.\d+)?)$", t)
    if m_special:
        item_name = m_special.group(1).strip().title()
        price = float(m_special.group(2))
        db.set_special(today, item_name, price)
        return f"Today's special set: {item_name} — ₹{int(price)}"

    # "dal sold out"
    if "sold out" in t:
        item_name = t.replace("sold out", "").strip()
        if not item_name:
            return "Usage: <item name> sold out"
        matched = _find_menu_item(item_name)
        if not matched:
            return f"Couldn't find '{item_name}' in the menu."
        avail = db.get_available_ids(today)
        db.set_availability(today, [], [matched["id"]])
        return f"Marked {matched['name']} as sold out."

    # "chola bhatura back"
    if t.endswith(" back"):
        item_name = t[:-4].strip()
        if not item_name:
            return "Usage: <item name> back"
        matched = _find_menu_item(item_name)
        if not matched:
            return f"Couldn't find '{item_name}' in the menu."
        db.set_availability(today, [matched["id"]], [])
        return f"Marked {matched['name']} as available."

    return "Commands:\n• <item> sold out\n• <item> back\n• special <name> <price>\n• all on"


def _find_menu_item(query: str) -> dict | None:
    """Fuzzy match a menu item name. Tries exact, then substring, then word match."""
    q = query.lower().strip()
    items = menu.load_menu()

    # Exact match (case-insensitive)
    for it in items:
        if it["name"].lower() == q:
            return it

    # Substring match
    for it in items:
        if q in it["name"].lower():
            return it

    # Word match — all words in query appear in item name
    words = q.split()
    for it in items:
        name_lower = it["name"].lower()
        if all(w in name_lower for w in words):
            return it

    return None
