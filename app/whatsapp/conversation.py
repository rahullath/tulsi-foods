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

KMS = {"1": 2.0, "2": 4.0, "3": 6.0}
KM_LABEL = {"1": "≤3 km", "2": "3–5 km", "3": "5–7 km"}

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
    if not sess["ctx"].get("seen"):
        sess["ctx"]["seen"] = True
        intro = (
            "Namaste! Welcome to Tulsi Foods, Mylapore. 🍛\n"
            "Order direct on WhatsApp — no app, no platform fees.\n"
            f"Tip: order before 11 AM for lunch & 5 PM for dinner to beat the rush.\n\n"
        )
        return [text(intro + render_categories())]
    return [text(render_categories())]


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

    # gentle add-on nudge only for the first item
    if was_empty and item["group"] in ADDON_GROUPS:
        chai = menu.get_item("masala-chai")
        if chai and menu.is_available("masala-chai"):
            out.append(buttons(
                f"Add a {chai['name']} for {money(chai['price'])} with your meal?",
                ["Yes, add chai", "No thanks"],
            ))
    return out


def _reorder_ask(sess: dict) -> list[dict]:
    oid = sess["ctx"].get("last_order_id")
    if not oid:
        return [text("No previous order found yet. Send MENU to start.")]
    o = db.get_order(oid)
    if not o:
        return [text("Couldn't find your last order. Send MENU to start.")]
    lines = ["Your last order:"]
    for it in o["items"]:
        lines.append(f"{it['name']} × {qty_disp(it['qty'])} — {money(it['price'] * it['qty'])}")
    lines.append(f"Total: {money(o['total'])}")
    sess["state"] = "reorder_confirm"
    sess["ctx"]["reorder_id"] = oid
    return [buttons("\n".join(lines) + "\n\nReorder this? Reply YES, or CANCEL.", ["YES", "CANCEL"])]


def _status(sess: dict) -> list[dict]:
    oid = sess["ctx"].get("last_order_id")
    if not oid:
        return [text("No order yet on this number. Send MENU to start.")]
    o = db.get_order(oid)
    label = STATUS_LABEL.get(o["status"], o["status"])
    return [text(f"Order #{oid} is {label}.")]


# ---------------------------------------------------------------- checkout

CHECKOUT_STEPS = {}


def _checkout_resume(sess: dict) -> list[dict]:
    state = sess["state"]
    if state == "checkout_name":
        return [text("Almost there! What name should the order be under?")]
    if state == "checkout_type":
        return [buttons("Delivery or pickup?", ["Delivery", "Pickup"])]
    if state == "checkout_address":
        return [text("Please send your delivery address (area, street, landmark).")]
    if state == "checkout_km":
        return [text("How far are you from the restaurant?\n1. ≤3 km\n2. 3–5 km\n3. 5–7 km")]
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
        lines.append(f"Delivery to: {ctx.get('address')} ({ctx.get('km_label')})")
    else:
        lines.append("Pickup from the restaurant.")
    lines.append(f"When: {ctx.get('when', 'Now')}")
    lines.append(f"Pay: {ctx.get('payment', 'COD')}")
    try:
        if ctx.get("order_type") == "delivery":
            quote = orders.delivery_quote(ctx["km"], total)
            fee = quote["fee"]
        else:
            fee = 0
    except orders.OrderError as e:
        return [text(e.message + "\nSend MENU to restart.")]
    lines.append(f"Delivery fee: {money(fee)}")
    lines.append(f"Total: {money(total + fee)}")
    sess["ctx"]["fee"] = fee
    return [buttons("\n".join(lines) + "\n\nReply YES to confirm, EDIT to change, or CANCEL.",
                    ["YES", "EDIT", "CANCEL"])]


# ---------------------------------------------------------------- entry point

def handle(wa_id: str, incoming: str, profile_name: str | None = None) -> list[dict]:
    sess = sessions.load(wa_id)
    if profile_name and not sess["ctx"].get("profile_name"):
        sess["ctx"]["profile_name"] = profile_name

    out = _route(sess, incoming or "")
    sessions.save(sess)
    return out


def _route(sess: dict, incoming: str) -> list[dict]:
    raw = incoming.strip()
    t = raw.upper()

    # YES handling (confirmations / add-on)
    if t in ("YES", "Y", "YES, ADD CHAI", "YES, ADD", "YES ADD CHAI"):
        if sess["state"] == "reorder_confirm":
            return _place_reorder(sess)
        if sess["state"] == "checkout_confirm":
            return _place_order(sess)
        # add-on yes
        chai = menu.get_item("masala-chai")
        if chai and menu.is_available("masala-chai") and sess["cart"]:
            sess["cart"]["masala-chai"] = sess["cart"].get("masala-chai", 0) + 1
            return [text(f"Added Masala Chai × 1. {cart_summary(sess)[0]}")]
        return _show_cart(sess)
    if t in ("NO", "N", "NO THANKS", "NO, ADD CHAI"):
        if sess["state"] in ("checkout_confirm",):
            return [text("Order not placed. Reply CART or MENU to continue.")]
        return _show_cart(sess)
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
            sess["state"] = "checkout_name"
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
        sess["ctx"]["address"] = raw[:200]
        sess["state"] = "checkout_km"
        return _checkout_resume(sess)
    if state == "checkout_km":
        if t in KMS:
            sess["ctx"]["km"] = KMS[t]
            sess["ctx"]["km_label"] = KM_LABEL[t]
            sess["state"] = "checkout_when"
            return _checkout_resume(sess)
        return [text("Reply 1, 2, or 3 for your distance.")]
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
        return _reorder_ask(sess)

    # fallback
    sess["state"] = "root"
    return [text(render_categories())]


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


def _place_order(sess: dict) -> list[dict]:
    ctx = sess["ctx"]
    items = [{"item_id": i, "qty": q} for i, q in sess["cart"].items()]
    try:
        result = orders.create_order(
            phone=sess["wa_id"],
            name=ctx.get("name") or ctx.get("profile_name") or "Customer",
            address=ctx.get("address"),
            order_type=ctx.get("order_type") or "delivery",
            km=ctx.get("km"),
            payment_method="upi" if ctx.get("payment") == "UPI" else "cod",
            instructions=None,
            scheduled_at=ctx.get("scheduled_at"),
            items=items,
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
    for k in ("name", "address", "km", "km_label", "when", "scheduled_at", "payment", "order_type", "fee"):
        sess["ctx"].pop(k, None)
    msg = (
        f"Order #{oid} confirmed ✅\n"
        f"Total: {money(result['total'])} ({payment})\n"
        f"{'Pickup' if order_type == 'pickup' else 'Delivery'} — {when}\n"
        "We'll update you here as it's prepared. Thanks!"
    )
    return [text(msg)]


def _place_reorder(sess: dict) -> list[dict]:
    oid = sess["ctx"].get("reorder_id")
    o = db.get_order(oid) if oid else None
    if not o:
        return [text("Couldn't find that order. Send MENU.")]
    items = [{"item_id": it["item_id"], "qty": it["qty"]} for it in o["items"]]
    try:
        result = orders.create_order(
            phone=sess["wa_id"],
            name=o.get("customer_name") or sess["ctx"].get("profile_name") or "Customer",
            address=o.get("customer_address"),
            order_type=o["order_type"],
            km=o["order_type"] == "delivery" and 2.0 or None,
            payment_method=o["payment_method"],
            items=items,
        )
    except orders.OrderError as e:
        return [text(e.message + "\nSend MENU to restart.")]
    sess["ctx"]["last_order_id"] = result["order_id"]
    sess["cart"] = {}
    sess["state"] = "root"
    return [text(f"Order #{result['order_id']} placed ✅ Total: {money(result['total'])}")]
