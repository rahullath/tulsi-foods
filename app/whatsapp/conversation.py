"""WhatsApp conversation state machine.

Pure logic: `handle(wa_id, text)` returns a list of outbound messages
({"type": "text"|"buttons", "text": ...}). No network calls — the webhook
layer and the REPL both drive it, so the full flow is testable without
WhatsApp credentials or a public URL.
"""
from .. import db, menu, orders
from . import sessions

ITEM_PAGE = 15
ADDON_GROUPS = {"Thalis & Combos", "Parathas & Breads", "Chaats & Snacks",
                "Starters", "Soups & Rice", "Sabzi", "Italian", "Specialities"}

# Upsell suggestions keyed by item group
UPSELL_MAP = {
    "Thalis & Combos": ["raita-250ml", "masala-chai"],
    "Parathas & Breads": ["masala-chai", "raita-250ml"],
    "Chaats & Snacks": ["masala-chai"],
    "Sabzi": ["masala-chai"],
    "Starters": ["masala-chai"],
}

# Minimal price upsell items (fallback if specific items not in menu)
UPSELL_FALLBACK = {
    "raita-250ml": {"id": "raita-250ml", "name": "Raita (250ml)", "price": 35},
    "masala-chai": {"id": "masala-chai", "name": "Masala Chai", "price": 51},
}

STATUS_LABEL = {
    "new": "just placed",
    "preparing": "being prepared",
    "ready": "ready",
    "out_for_delivery": "out for delivery",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


def text(body: str) -> dict:
    return {"type": "text", "text": body}


def buttons(body: str, btns: list[str]) -> dict:
    return {"type": "buttons", "text": body, "buttons": btns}


def money(n) -> str:
    return "₹" + str(round(float(n)))


def qty_disp(q) -> str:
    f = float(q)
    return str(int(f)) if f == int(f) else str(f)


def _groups():
    return menu.grouped()


def _available_items(group: dict) -> list[dict]:
    return [it for it in group["items"] if it["available"]]


# ---------------------------------------------------------------- rendering

def render_categories() -> str:
    lines = ["Here's today's menu:"]
    for i, g in enumerate(_groups(), 1):
        avail = sum(1 for it in g["items"] if it["available"])
        lines.append(f"{i}. {g['group']} ({avail} items)")
    lines.append("")
    lines.append("Reply with a number to see items. Also try: CART, CHECKOUT, REORDER, STATUS, HELP.")
    return "\n".join(lines)


CATEGORY_SECTIONS = [
    {
        "title": "MAINS",
        "rows": [
            {"id": "cat_0", "title": "Thalis & Combos"},
            {"id": "cat_1", "title": "Sabzi"},
            {"id": "cat_2", "title": "Parathas & Breads"},
        ],
    },
    {
        "title": "SNACKS & SIDES",
        "rows": [
            {"id": "cat_3", "title": "Chaats & Snacks"},
            {"id": "cat_4", "title": "Starters"},
            {"id": "cat_5", "title": "Soups & Rice"},
        ],
    },
    {
        "title": "EXTRAS",
        "rows": [
            {"id": "cat_6", "title": "Italian"},
            {"id": "cat_7", "title": "Specialities"},
            {"id": "cat_8", "title": "Desserts"},
            {"id": "cat_9", "title": "Beverages"},
        ],
    },
]


def render_categories_list() -> dict:
    groups = _groups()
    # Map group name -> section
    group_section = {
        "Thalis & Combos": "MAINS",
        "Sabzi": "MAINS",
        "Parathas & Breads": "MAINS",
        "Chaats & Snacks": "SNACKS & SIDES",
        "Starters": "SNACKS & SIDES",
        "Soups & Rice": "SNACKS & SIDES",
    }
    sections: dict[str, list[dict]] = {"MAINS": [], "SNACKS & SIDES": [], "EXTRAS": []}
    for i, g in enumerate(groups):
        avail = _available_items(g)
        total = len(g["items"])
        prices = [it["price"] for it in avail] or [0]
        price_min = money(min(prices))
        price_max = money(max(prices))
        label = f"{total} item{'s' if total != 1 else ''}"
        if total != len(g["items"]):
            label = f"{total} of {len(g['items'])} items"
        desc = f"{label} · {price_min}–{price_max}" if price_min != price_max else label
        row = {"id": f"cat_{i}", "title": g["group"], "description": desc}
        sec = group_section.get(g["group"], "EXTRAS")
        sections[sec].append(row)
    return {
        "type": "list",
        "text": "What would you like to order?",
        "button": "Browse menu",
        "sections": [{"title": k, "rows": v} for k, v in sections.items() if v],
    }


def _category_section(index: int) -> str:
    if index <= 2:
        return "MAINS"
    if index <= 5:
        return "SNACKS & SIDES"
    return "EXTRAS"


def render_items(group_index: int, page: int) -> tuple[str, int | None]:
    groups = _groups()
    if not (0 <= group_index < len(groups)):
        return "Sorry, that category doesn't exist.", None
    g = groups[group_index]
    avail = _available_items(g)
    total_pages = max(1, (len(avail) + ITEM_PAGE - 1) // ITEM_PAGE)
    if page >= total_pages:
        page = 0
    chunk = avail[page * ITEM_PAGE:(page + 1) * ITEM_PAGE]
    base = page * ITEM_PAGE
    lines = [f"{g['group']} — reply a number to add. e.g. '2' or '3 x2':"]
    for j, it in enumerate(chunk, 1):
        tag = " ⭐" if it.get("popular") else ""
        lines.append(f"{base + j}. {it['name']}{tag} — {money(it['price'])}")
    if page + 1 < total_pages:
        lines.append(f"")
        lines.append(f"Send 0 for more ({total_pages - page - 1} more page(s)).")
    lines.append("Send BACK for categories, CART to review.")
    return "\n".join(lines), page


def cart_summary(sess: dict, show_index: bool = False) -> tuple[str, float]:
    ids = list(sess["cart"].keys())
    lines = ["Your cart:"]
    total = 0.0
    for pos, item_id in enumerate(ids, 1):
        qty = sess["cart"][item_id]
        m = menu.get_item(item_id)
        if not m:
            continue
        line_total = m["price"] * qty
        total += line_total
        prefix = f"{pos}. " if show_index else ""
        lines.append(f"{prefix}{m['name']} × {qty_disp(qty)} — {money(line_total)}")
    if not lines[1:]:
        return "Your cart is empty.", 0.0
    lines.append(f"Subtotal: {money(total)}")
    return "\n".join(lines), total


# ---------------------------------------------------------------- actions

def _show_categories(sess: dict) -> list[dict]:
    sess["state"] = "root"
    sess["ctx"].pop("cat_index", None)
    sess["ctx"].pop("page", None)
    msgs = []
    if not sess["ctx"].get("seen"):
        sess["ctx"]["seen"] = True
        msgs.append(text(
            "Namaste! Welcome to Tulsi Foods, Mylapore. 🍛\n"
            "Order direct on WhatsApp — no app, no platform fees.\n"
            f"Tip: order before 11 AM for lunch & 5 PM for dinner to beat the rush."
        ))
    # Show daily special if set
    from .. import db as _db
    special = _db.get_special()
    if special:
        msgs.append(text(
            f"Today's special: {special['item_name']} — ₹{int(special['price'])} ✨"
        ))
    msgs.append(render_categories_list())
    return msgs


def _show_cart(sess: dict) -> list[dict]:
    body, total = cart_summary(sess, show_index=True)
    if not sess["cart"]:
        sess["state"] = "root"
        return [text(body + "\nSend MENU to order.")]
    sess["state"] = "cart"
    return [buttons(
        body + "\n\nCHECKOUT to place order · REMOVE <n> to remove · CLEAR to empty · MENU to browse",
        ["CHECKOUT", "MENU"],
    )]


def _add_item(sess: dict, group_index: int, page: int, raw: str) -> list[dict]:
    """Handle 'N' or 'N x2' from the item listing."""
    groups = _groups()
    g = groups[group_index]
    avail = _available_items(g)
    tokens = raw.strip().split()
    try:
        idx = int(tokens[0])
        qty = float(tokens[2]) if len(tokens) >= 3 and tokens[1].lower() == "x" else (
            float(tokens[1].lstrip("x")) if len(tokens) >= 2 else 1.0)
    except (ValueError, IndexError):
        return [text("Hmm, I didn't get that. Try like '2' or '3 x2'.")]
    if qty <= 0:
        return [text("Quantity must be more than zero.")]

    if idx == 0:  # next page
        page += 1
        body, page = render_items(group_index, page)
        sess["ctx"]["page"] = page
        return [text(body)]

    pos = page * ITEM_PAGE + idx - 1
    if not (0 <= pos < len(avail)):
        return [text("That number isn't in this list. Send 0 for more, or BACK.")]
    item = avail[pos]
    was_empty = not sess["cart"]
    sess["cart"][item["id"]] = sess["cart"].get(item["id"], 0) + qty

    total = sum(m["price"] * sess["cart"][m["id"]] for m in menu.load_menu()
                if m["id"] in sess["cart"])
    out = [text(f"Added {item['name']} × {qty_disp(qty)} ({money(item['price'] * qty)}). Cart: {money(total)}")]

    # Context-aware upsell for the first item
    if was_empty:
        upsell_ids = UPSELL_MAP.get(item["group"], [])
        available_upsells = [
            menu.get_item(uid) for uid in upsell_ids
            if menu.get_item(uid) and menu.is_available(uid)
        ]
        if available_upsells:
            btns = [u["id"] for u in available_upsells[:2]]
            btns.append("No thanks")
            names = " or ".join(f"{u['name']} for {money(u['price'])}" for u in available_upsells[:2])
            out.append(buttons(
                f"{item['group'].split()[0].rstrip('&s')} goes well with {names}. Add one?",
                btns,
            ))
    return out


def _reorder_ask(sess: dict) -> list[dict]:
    phone = sess["wa_id"]
    orders = db.customer_orders(phone, limit=5)
    if not orders:
        return [text("No previous order found yet. Send MENU to start.")]
    # Show last order with items
    o = db.get_order(orders[0]["id"])
    if not o:
        return [text("Couldn't find your last order. Send MENU to start.")]
    excluded = sess["ctx"].get("reorder_excluded", [])
    lines = [f"Your last order · {_format_order_time(o['created_at'])}"]
    for i, it in enumerate(o["items"]):
        if it["item_id"] in excluded:
            lines.append(f"~~{it['name']} × {qty_disp(it['qty'])} — {money(it['price'] * it['qty'])}~~")
        else:
            lines.append(f"{it['name']} × {qty_disp(it['qty'])} — {money(it['price'] * it['qty'])}")
    active_items = [it for it in o["items"] if it["item_id"] not in excluded]
    active_total = sum(it["price"] * it["qty"] for it in active_items)
    lines.append(f"Total: {money(active_total)}")

    btns = ["Place this order", "Cancel"]
    if len(orders) > 1:
        btns.insert(1, "Older orders")

    sess["state"] = "reorder_confirm"
    sess["ctx"]["reorder_id"] = o["id"]
    sess["ctx"]["reorder_orders"] = [{"id": ordr["id"], "total": ordr["total"], "created_at": ordr["created_at"]} for ordr in orders]
    return [buttons(
        "\n".join(lines) + "\n\nREMOVE <n> to remove an item (e.g. 'REMOVE 2')",
        btns,
    )]


def _format_order_time(created_at: str) -> str:
    """Format order time for display."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(created_at)
        now = datetime.now()
        if dt.date() == now.date():
            return "today"
        from datetime import timedelta
        if dt.date() == (now - timedelta(days=1)).date():
            return "yesterday"
        return dt.strftime("%a")
    except (ValueError, TypeError):
        return ""


def _reorder_older(sess: dict) -> list[dict]:
    """Show older orders for reorder selection."""
    orders_list = sess["ctx"].get("reorder_orders", [])
    if len(orders_list) <= 1:
        return [text("No older orders found.")]
    lines = ["Your recent orders:"]
    for i, o in enumerate(orders_list):
        t = _format_order_time(o["created_at"])
        lines.append(f"{i + 1}. {t} · {money(o['total'])}")
    lines.append("\nSend a number to reorder, or CANCEL.")
    sess["state"] = "reorder_older"
    return [text("\n".join(lines))]


def _status(sess: dict) -> list[dict]:
    oid = sess["ctx"].get("last_order_id")
    if not oid:
        return [text("No order yet on this number. Send MENU to start.")]
    o = db.get_order(oid)
    label = STATUS_LABEL.get(o["status"], o["status"])
    msg = f"Order #{oid} is {label}."
    if o.get("sr_tracking_url"):
        msg += f"\nTrack: {o['sr_tracking_url']}"
    if o.get("sr_courier"):
        msg += f"\nCourier: {o['sr_courier']}"
    return [text(msg)]


# ---------------------------------------------------------------- checkout

CHECKOUT_STEPS = {}


MIN_ORDER_SUGGESTIONS = ["masala-chai", "samosa-2-pcs", "aloo-tikki-chaat", "manchow-soup"]


def _min_order_nudge(sess: dict, subtotal: float, zone_min: int = 250) -> list[dict] | None:
    """Show min-order nudge if cart is below minimum. Returns messages or None."""
    if subtotal >= zone_min:
        return None
    gap = zone_min - subtotal
    # Find available items that bridge the gap
    suggestions = []
    for uid in MIN_ORDER_SUGGESTIONS:
        it = menu.get_item(uid)
        if it and menu.is_available(uid) and it["price"] <= gap + 50:
            suggestions.append(it)
        if len(suggestions) >= 2:
            break
    # If no specific suggestions, find cheap popular items
    if not suggestions:
        for it in menu.load_menu():
            if it.get("popular") and menu.is_available(it["id"]) and it["price"] <= gap + 50:
                suggestions.append(it)
            if len(suggestions) >= 2:
                break

    btns = [s["id"] for s in suggestions]
    btns.append(f"Order anyway (+₹30)")
    lines = [f"₹{int(gap)} short of the ₹{zone_min} minimum."]
    if suggestions:
        sug_text = " or ".join(f"{s['name']} for {money(s['price'])}" for s in suggestions)
        lines.append(f"Add one of these?")
    else:
        lines.append(f"Add something worth ₹{int(gap)}+.")
    return [buttons("\n".join(lines), btns)]


def _checkout_resume(sess: dict) -> list[dict]:
    state = sess["state"]
    ctx = sess["ctx"]
    if state == "checkout_name":
        return [text("Almost there! What name should the order be under?")]
    if state == "checkout_type":
        return [buttons("Delivery or pickup?", ["Delivery", "Pickup"])]
    if state == "checkout_address":
        # Check if we have a saved address
        saved = ctx.get("saved_address")
        if saved:
            return [buttons(
                f"Deliver to: {saved}?\nReply YES or send a new address.",
                ["YES, same address"]
            )]
        return [text("Please send your full delivery address (street, area, landmark).")]
    if state == "checkout_pincode":
        saved_pin = ctx.get("saved_pincode")
        if saved_pin:
            return [buttons(
                f"Pincode: {saved_pin}?\nReply YES or send a new 6-digit pincode.",
                ["YES, same pincode"]
            )]
        return [text("What's your 6-digit pincode? (e.g. 600018)")]
    if state == "checkout_when":
        return [text("When do you want it?\nSend NOW, or a time like 12:30 for a pre-order.")]
    if state == "checkout_payment":
        return [buttons("How would you like to pay?", ["Cash on delivery", "UPI"])]
    if state == "checkout_confirm":
        return _summary(sess)
    return _show_cart(sess)


def _summary(sess: dict) -> list[dict]:
    ctx = sess["ctx"]
    body, total = cart_summary(sess)
    lines = [body, ""]
    if ctx.get("order_type") == "delivery":
        addr = ctx.get("address", "")
        pin = ctx.get("pincode", "")
        lines.append(f"Delivery to: {addr} ({pin})")
    else:
        lines.append("Pickup from the restaurant.")
    lines.append(f"When: {ctx.get('when', 'Now')}")
    lines.append(f"Pay: {ctx.get('payment', 'COD')}")
    # Delivery fee: zone estimate (actual calculated at dispatch)
    fee = 0
    if ctx.get("order_type") == "delivery" and total < 700:
        fee = 30  # Zone A estimate
    # Order-anyway surcharge
    if ctx.get("order_anyway_fee"):
        fee += 30
        lines.append(f"Small order fee: {money(30)}")
    packing = orders.packing_fee_for(total)
    gst = orders.gst_for(total + packing)
    if packing:
        lines.append(f"Packing charge: {money(packing)}")
    if gst:
        lines.append(f"GST: {money(gst)}")
    lines.append(f"Delivery fee: {money(fee)} (approx, confirmed at dispatch)")
    lines.append(f"Total: {money(total + packing + gst + fee)}")
    sess["ctx"]["fee"] = fee
    return [buttons("\n".join(lines) + "\n\nReply YES to confirm, EDIT to change, or CANCEL.",
                    ["YES", "EDIT", "CANCEL"])]


# ---------------------------------------------------------------- entry point

def handle(wa_id: str, incoming: str, profile_name: str | None = None,
           lat: str | None = None, lng: str | None = None) -> list[dict]:
    sess = sessions.load(wa_id)
    if profile_name and not sess["ctx"].get("profile_name"):
        sess["ctx"]["profile_name"] = profile_name
    # Store GPS coords if provided (from WhatsApp location message)
    if lat and lng:
        sess["ctx"]["lat"] = lat
        sess["ctx"]["lng"] = lng

    out = _route(sess, incoming or "")
    sessions.save(sess)
    return out


def _route(sess: dict, incoming: str) -> list[dict]:
    raw = incoming.strip()
    t = raw.upper()

    # YES handling (confirmations / add-on / address memory)
    if t in ("YES", "Y"):
        if sess["state"] == "reorder_confirm":
            return _place_reorder(sess)
        if sess["state"] == "checkout_confirm":
            return _place_order(sess)
        # Address memory: YES = use saved address
        if sess["state"] == "checkout_address" and sess["ctx"].get("saved_address"):
            sess["ctx"]["address"] = sess["ctx"]["saved_address"]
            sess["state"] = "checkout_pincode"
            return _checkout_resume(sess)
        # Pincode memory: YES = use saved pincode
        if sess["state"] == "checkout_pincode" and sess["ctx"].get("saved_pincode"):
            sess["ctx"]["pincode"] = sess["ctx"]["saved_pincode"]
            sess["state"] = "checkout_when"
            return _checkout_resume(sess)
        return _show_cart(sess)
    # Handle upsell button replies (item IDs like "raita", "masala-chai")
    if t in ("NO", "N", "NO THANKS"):
        if sess["state"] in ("checkout_confirm",):
            return [text("Order not placed. Reply CART or MENU to continue.")]
        if sess["state"] == "checkout_address":
            return [text("Please send your full delivery address (street, area, landmark).\nOr tap 📎 → Location to share your live location for precise delivery.")]
        if sess["state"] == "checkout_pincode":
            return [text("What's your 6-digit pincode? (e.g. 600018)")]
        return _show_cart(sess)
    upsell_item = menu.get_item(t.lower())
    if upsell_item and sess["cart"]:
        sess["cart"][upsell_item["id"]] = sess["cart"].get(upsell_item["id"], 0) + 1
        return [text(f"Added {upsell_item['name']} × 1. {cart_summary(sess)[0]}")]
    # "Order anyway" from min-order nudge
    if t.startswith("ORDER ANYWAY") or t.startswith("ORDERANYWAY"):
        sess["ctx"]["order_anyway_fee"] = True
        _load_saved_address(sess)
        sess["state"] = "checkout_name"
        if sess["ctx"].get("name") or sess["ctx"].get("profile_name"):
            sess["state"] = "checkout_type"
            return _checkout_resume(sess)
        return [text("Almost there! What name should the order be under?")]
    if t in ("EDIT",):
        sess["state"] = "checkout_name"
        return [text("Let's fix it up. What name should the order be under?")]
    if t in ("CANCEL", "CLEAR"):
        sess["cart"] = {}
        sess["state"] = "root"
        sess["ctx"].pop("order_type", None)
        return [text("Order cancelled / cart cleared. Send MENU to start fresh.")]

    # global commands
    if t in ("MENU", "BACK", "B"):
        return _show_categories(sess)
    # Handle list reply (cat_N) globally — can jump to any category from any state
    if t.startswith("CAT_"):
        try:
            gi = int(t.split("_", 1)[1])
        except (ValueError, IndexError):
            gi = -1
        groups = _groups()
        if 0 <= gi < len(groups):
            sess["ctx"]["cat_index"] = gi
            sess["ctx"]["page"] = 0
            sess["state"] = "items"
            body, page = render_items(gi, 0)
            return [text(body)]
        return [text("That category doesn't exist. Send MENU to start over.")]
    if t == "CART":
        return _show_cart(sess)
    if t == "HELP":
        return [text(
            "Commands: MENU · CART · CHECKOUT · REORDER · STATUS · CLEAR · HELP\n"
            "Browse by number, add like '3 x2'. Tip: order before 11 AM (lunch) and 5 PM (dinner)."
        )]
    if t == "STATUS":
        return _status(sess)
    if t == "REORDER":
        return _reorder_ask(sess)

    state = sess["state"]

    if state == "root":
        if t.isdigit() and 1 <= int(t) <= len(_groups()):
            gi = int(t) - 1
            sess["ctx"]["cat_index"] = gi
            sess["ctx"]["page"] = 0
            sess["state"] = "items"
            body, page = render_items(gi, 0)
            return [text(body)]
        if not sess["ctx"].get("seen"):
            return _show_categories(sess)
        return [text("Send a category number, or MENU / CART / CHECKOUT / REORDER / STATUS / HELP.")]

    if state == "items":
        gi = sess["ctx"].get("cat_index", 0)
        page = sess["ctx"].get("page", 0)
        if t.startswith("REMOVE"):
            return _remove_from_cart(sess, raw)
        return _add_item(sess, gi, page, raw)

    if state == "cart":
        if t == "CHECKOUT" or t.startswith("CHECKOUT"):
            if not sess["cart"]:
                return [text("Cart is empty. Send MENU to order.")]
            # Check minimum order
            _, subtotal = cart_summary(sess)
            nudge = _min_order_nudge(sess, subtotal)
            if nudge:
                return nudge
            # Load saved address from customer record
            _load_saved_address(sess)
            sess["state"] = "checkout_name"
            # Skip name if we already have it
            if sess["ctx"].get("name") or sess["ctx"].get("profile_name"):
                sess["state"] = "checkout_type"
                return _checkout_resume(sess)
            return [text("Almost there! What name should the order be under?")]
        if t.startswith("REMOVE"):
            return _remove_from_cart(sess, raw)
        return _show_cart(sess)

    # checkout steps
    if state == "checkout_name":
        sess["ctx"]["name"] = raw[:60]
        sess["state"] = "checkout_type"
        return _checkout_resume(sess)
    if state == "checkout_type":
        if raw.lower().startswith("d") or t in ("1",):
            sess["ctx"]["order_type"] = "delivery"
            sess["state"] = "checkout_address"
            return _checkout_resume(sess)
        if raw.lower().startswith("p") or t in ("2",):
            sess["ctx"]["order_type"] = "pickup"
            sess["state"] = "checkout_when"
            return _checkout_resume(sess)
        return [text("Reply D for delivery or P for pickup.")]
    if state == "checkout_address":
        # Accept location message as address (coords stored in ctx by handle())
        if raw.startswith("[Location:"):
            sess["ctx"]["address"] = sess["ctx"].get("address") or raw[:200]
        else:
            sess["ctx"]["address"] = raw[:200]
        sess["state"] = "checkout_pincode"
        return _checkout_resume(sess)
    if state == "checkout_pincode":
        # Validate 6-digit pincode
        pin = raw.replace(" ", "")
        if len(pin) == 6 and pin.isdigit():
            sess["ctx"]["pincode"] = pin
            sess["state"] = "checkout_when"
            return _checkout_resume(sess)
        return [text("Please enter a valid 6-digit pincode (e.g. 600018).")]
    if state == "checkout_when":
        if t == "NOW":
            sess["ctx"]["when"] = "Now"
            sess["ctx"]["scheduled_at"] = None
        else:
            sess["ctx"]["when"] = raw
            sess["ctx"]["scheduled_at"] = raw
        sess["state"] = "checkout_payment"
        return _checkout_resume(sess)
    if state == "checkout_payment":
        if t in ("COD", "1") or raw.lower().startswith("cash"):
            sess["ctx"]["payment"] = "COD"
        elif t in ("UPI", "2"):
            sess["ctx"]["payment"] = "UPI"
        else:
            return [text("Reply COD or UPI.")]
        sess["state"] = "checkout_confirm"
        return _summary(sess)

    if state == "reorder_confirm":
        if t in ("PLACE THIS ORDER", "PLACE", "PLACEORDER"):
            return _place_reorder(sess)
        if t in ("OLDER ORDERS", "OLDER"):
            return _reorder_older(sess)
        if t.startswith("REMOVE"):
            return _reorder_remove(sess, raw)
        return _reorder_ask(sess)

    if state == "reorder_older":
        if t.isdigit():
            idx = int(t) - 1
            orders_list = sess["ctx"].get("reorder_orders", [])
            if 0 <= idx < len(orders_list):
                sess["ctx"]["reorder_id"] = orders_list[idx]["id"]
                sess["ctx"]["reorder_excluded"] = []
                sess["state"] = "reorder_confirm"
                return _reorder_ask(sess)
        return [text("Send a number to reorder, or CANCEL.")]

    # fallback
    sess["state"] = "root"
    return [text(render_categories())]


def _load_saved_address(sess: dict) -> None:
    """Load saved address/pincode from customer record for address memory."""
    phone = sess["wa_id"]
    customer = db.get_customer(phone)
    if customer:
        if customer.get("address"):
            sess["ctx"]["saved_address"] = customer["address"]
        if customer.get("pincode"):
            sess["ctx"]["saved_pincode"] = customer["pincode"]
        if customer.get("name") and not sess["ctx"].get("name"):
            sess["ctx"]["name"] = customer["name"]


def _remove_from_cart(sess: dict, raw: str) -> list[dict]:
    tokens = raw.split()
    if len(tokens) < 2 or not tokens[1].isdigit():
        return [text("Usage: REMOVE <number> (see your cart list).")]
    pos = int(tokens[1])
    ids = list(sess["cart"].keys())
    if not (1 <= pos <= len(ids)):
        return [text("That number isn't in your cart.")]
    item_id = ids[pos - 1]
    del sess["cart"][item_id]
    return _show_cart(sess)


def _reorder_remove(sess: dict, raw: str) -> list[dict]:
    """Remove an item from the reorder list by index."""
    tokens = raw.split()
    if len(tokens) < 2 or not tokens[1].isdigit():
        return [text("Usage: REMOVE <number> (see item numbers in the list).")]
    pos = int(tokens[1])
    o = db.get_order(sess["ctx"].get("reorder_id"))
    if not o:
        return [text("Order not found.")]
    items = o["items"]
    if not (1 <= pos <= len(items)):
        return [text("That number isn't in the order list.")]
    excluded = sess["ctx"].setdefault("reorder_excluded", [])
    item_id = items[pos - 1]["item_id"]
    if item_id in excluded:
        excluded.remove(item_id)
    else:
        excluded.append(item_id)
    return _reorder_ask(sess)


def _place_order(sess: dict) -> list[dict]:
    ctx = sess["ctx"]
    items = [{"item_id": i, "qty": q} for i, q in sess["cart"].items()]
    try:
        result = orders.create_order(
            phone=sess["wa_id"],
            name=ctx.get("name") or ctx.get("profile_name") or "Customer",
            address=ctx.get("address"),
            order_type=ctx.get("order_type") or "delivery",
            pincode=ctx.get("pincode"),
            payment_method="upi" if ctx.get("payment") == "UPI" else "cod",
            instructions=None,
            scheduled_at=ctx.get("scheduled_at"),
            items=items,
            lat=ctx.get("lat"),
            lng=ctx.get("lng"),
        )
    except orders.OrderError as e:
        return [text(e.message + "\nSend MENU to restart.")]

    oid = result["order_id"]
    sess["ctx"]["last_order_id"] = oid
    when = ctx.get("when", "Now")
    payment = ctx.get("payment")
    order_type = ctx.get("order_type")
    sess["cart"] = {}
    sess["state"] = "root"
    for k in ("name", "address", "pincode", "saved_address", "saved_pincode",
              "when", "scheduled_at", "payment", "order_type", "fee"):
        sess["ctx"].pop(k, None)
    msg = (
        f"Order #{oid} confirmed ✅\n"
        f"Total: {money(result['total'])} ({payment})\n"
        f"{'Pickup' if order_type == 'pickup' else 'Delivery'} — {when}\n"
        "We'll WhatsApp you when your food is on its way! 🛵"
    )
    return [text(msg)]


def _place_reorder(sess: dict) -> list[dict]:
    oid = sess["ctx"].get("reorder_id")
    o = db.get_order(oid) if oid else None
    if not o:
        return [text("Couldn't find that order. Send MENU.")]
    excluded = sess["ctx"].get("reorder_excluded", [])
    items = [{"item_id": it["item_id"], "qty": it["qty"]}
             for it in o["items"] if it["item_id"] not in excluded]
    if not items:
        return [text("All items were removed. Send MENU to start fresh.")]
    try:
        result = orders.create_order(
            phone=sess["wa_id"],
            name=o.get("customer_name") or sess["ctx"].get("profile_name") or "Customer",
            address=o.get("delivery_address") or o.get("customer_address"),
            order_type=o["order_type"],
            pincode=o.get("delivery_pincode"),
            payment_method=o["payment_method"],
            items=items,
        )
    except orders.OrderError as e:
        return [text(e.message + "\nSend MENU to restart.")]
    sess["ctx"]["last_order_id"] = result["order_id"]
    sess["cart"] = {}
    sess["state"] = "root"
    return [text(f"Order #{result['order_id']} placed ✅ Total: {money(result['total'])}")]
