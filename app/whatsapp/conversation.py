"""WhatsApp ordering bot: catalogue first, buttons everywhere, no typing.

Pure logic: `handle(...)` returns a list of outbound message dicts; the
webhook layer sends them (app/whatsapp/client.send_outbound). No network
calls here, so the whole flow runs in tests and scripts/whatsapp_repl.py.

The flow (Oct 2026):
  hi / anything      -> the menu as WhatsApp's own catalogue (+ Reorder /
                        Track for returning customers)
  cart from catalogue -> cart summary, Delivery / Pickup
  Delivery           -> address form (India) or typed address, then a
                        location pin, which sets the fixed fee band
  When               -> As soon as possible, or a lunch/dinner window
  Pay                -> UPI or Cash
  Summary            -> Place order -> orders.create_order (POS, kitchen,
                        WhatsApp confirmation template), UPI pay button
Typed words still work at any point: MENU, CART, TRACK, REORDER, HELP, CANCEL.

Message dicts:
  {"type": "text", "text"}
  {"type": "buttons", "text", "buttons": [(id, title) | title, ...]}  (max 3)
  {"type": "list", "text", "button", "sections": [{"title", "rows": [{"id", "title", "description"?}]}]}
  {"type": "catalog", "text"}                      whole menu, native catalogue view
  {"type": "products", "header", "text", "sections": [{"title", "ids": [...]}]}
  {"type": "location_request", "text"}
  {"type": "address", "text", "values": {...}}      India address form
  {"type": "cta", "text", "label", "url"}           one link button
"""
from datetime import datetime, timedelta, timezone

from .. import db, menu, orders
from . import sessions

SITE = "https://tulsifoods.app"
PICKS_LIMIT = 30          # WhatsApp product_list maximum
PICKS_PER_SECTION = 6

STATUS_LABEL = {
    "new": "placed, waiting for the kitchen to accept it",
    "preparing": "being cooked",
    "ready": "packed and ready",
    "out_for_delivery": "on its way",
    "delivered": "delivered",
    "cancelled": "cancelled",
}

HELP_TEXT = (
    "Tap *View catalogue* to see the menu, add dishes, then send the cart.\n"
    "You can also type MENU, TRACK, REORDER or CANCEL any time."
)


# ---------------------------------------------------------------- builders

def text(body: str) -> dict:
    return {"type": "text", "text": body}


def buttons(body: str, btns: list) -> dict:
    return {"type": "buttons", "text": body, "buttons": btns}


def money(n) -> str:
    v = round(float(n), 2)
    return "₹" + (str(int(v)) if v == int(v) else f"{v:.2f}")


def qty_disp(q) -> str:
    f = float(q)
    return str(int(f)) if f == int(f) else str(f)


def _is_indian(wa_id: str) -> bool:
    d = "".join(ch for ch in wa_id if ch.isdigit())
    return len(d) == 10 or (len(d) == 12 and d.startswith("91"))


def _phone_display(wa_id: str) -> str:
    d = "".join(ch for ch in wa_id if ch.isdigit())
    return "+" + d if len(d) > 10 else "+91" + d


# ---------------------------------------------------------------- menu

def catalog_message(body: str | None = None) -> dict:
    return {"type": "catalog", "text": body or (
        "Here's today's menu. Tap *View catalogue*, add what you'd like, "
        "then tap the cart and *Send* to order.")}


def picks_message() -> dict | None:
    """Popular dishes available today, grouped by category, as a tappable
    product list (built at send time, so sold-out dishes never show)."""
    sections, total = [], 0
    for g in menu.grouped():
        items = [it for it in g["items"] if it["available"] and it.get("popular")]
        items = items[:PICKS_PER_SECTION]
        if not items or len(sections) == 10:
            continue
        items = items[: PICKS_LIMIT - total]
        if not items:
            break
        sections.append({"title": g["group"][:24], "ids": [it["id"] for it in items]})
        total += len(items)
    if not sections:
        return None
    return {"type": "products", "header": "Popular at Tulsi Foods",
            "text": "Our most-ordered dishes that are available today.",
            "sections": sections}


def _welcome(sess: dict) -> list[dict]:
    sess["state"] = "root"
    out = []
    name = (sess["ctx"].get("profile_name") or "").split(" ")[0]
    if not sess["ctx"].get("seen"):
        sess["ctx"]["seen"] = True
        hello = f"Namaste{' ' + name if name else ''}! Welcome to Tulsi Foods, Mylapore 🍛"
        out.append(text(hello + "\nPure veg, home-style North Indian. Order right here, "
                        "no app and no platform fees."))
    special = db.get_special()
    if special:
        out.append(text(f"Today's special: {special['item_name']} — {money(special['price'])} ✨"))
    out.append(catalog_message())
    extra = []
    if db.customer_orders(sess["wa_id"], limit=1):
        extra += [("REORDER", "Reorder last"), ("TRACK", "Track order")]
    extra.append(("PICKS", "Popular dishes"))
    out.append(buttons("Or pick one:" if len(extra) > 1 else "Not sure what to get?", extra[:3]))
    return out


# ---------------------------------------------------------------- cart

def cart_summary(sess: dict) -> tuple[str, float]:
    lines, total = [], 0.0
    for item_id, qty in sess["cart"].items():
        m = menu.get_item(item_id)
        if not m:
            continue
        total += m["price"] * qty
        lines.append(f"{qty_disp(qty)} × {m['name']} — {money(m['price'] * qty)}")
    if not lines:
        return "Your cart is empty.", 0.0
    return "\n".join(lines) + f"\n*Subtotal: {money(total)}*", total


def _catalog_order(sess: dict, items: list[dict]) -> list[dict]:
    """A cart sent from the catalogue replaces the chat cart and starts
    checkout. Dishes finished for today are left out."""
    cart, skipped = {}, []
    for it in items:
        pid = str(it.get("id") or "")
        if pid.endswith("-half"):  # the feed's half SKU id (app/catalog.py)
            pid = pid[: -len("-half")] + menu.HALF_SUFFIX
        m = menu.get_item(pid)
        if not m:
            continue
        if not menu.is_available(m["id"]):
            skipped.append(m["name"])
            continue
        cart[m["id"]] = cart.get(m["id"], 0) + max(1, int(it.get("qty") or 1))
    if not cart:
        sess["state"] = "root"
        why = f"{', '.join(skipped)} {'is' if len(skipped) == 1 else 'are'} finished for today. " if skipped else ""
        return [text(f"Sorry, {why}Pick something else from the menu."), catalog_message()]
    sess["cart"] = cart
    out = [text(f"Finished for today, so left out: {', '.join(skipped)}.")] if skipped else []
    return out + _ask_order_type(sess)


def _ask_order_type(sess: dict) -> list[dict]:
    body, _ = cart_summary(sess)
    sess["state"] = "type"
    return [buttons(f"Your order:\n{body}\n\nDelivery or pickup?",
                    [("DELIVERY", "Delivery"), ("PICKUP", "Pickup"), ("EDIT", "Change cart")])]


# ---------------------------------------------------------------- address

def _ask_address(sess: dict) -> list[dict]:
    sess["state"] = "address"
    ctx = sess["ctx"]
    saved = db.get_customer(sess["wa_id"]) or {}
    if saved.get("address") and not ctx.get("asked_saved"):
        ctx["asked_saved"] = True
        ctx["saved_address"] = saved["address"]
        short = saved["address"][:300]
        return [buttons(f"Deliver to your last address?\n{short}",
                        [("SAVED", "Yes, same address"), ("NEWADDR", "New address")])]
    if _is_indian(sess["wa_id"]):
        return [{"type": "address", "text": "Where should we deliver? Fill in your address below.",
                 "values": {"name": ctx.get("profile_name") or "",
                            "phone_number": _phone_display(sess["wa_id"])}}]
    return [text("Please type your full delivery address: house/flat, street, area, landmark.")]


def _address_from_form(values: dict) -> str:
    parts = [values.get(k) for k in ("house_number", "floor_number", "tower_number",
                                     "building_name", "address", "landmark_area", "city")]
    line = ", ".join(p.strip() for p in parts if p and str(p).strip())
    pin = (values.get("in_pin_code") or "").strip()
    return f"{line} {pin}".strip()


def _ask_location(sess: dict) -> list[dict]:
    sess["state"] = "location"
    return [{"type": "location_request",
             "text": "Now share your location pin so the rider finds you. "
                     "It also sets your delivery fee (₹49–₹89 by distance)."}]


def _set_location(sess: dict, lat: str, lng: str) -> list[dict]:
    from ..delivery.estimate import estimate
    ctx = sess["ctx"]
    _, subtotal = cart_summary(sess)
    q = estimate(float(lat), float(lng), subtotal)
    if q.get("serviceable") is False:
        sess["state"] = "type"
        return [buttons(f"That pin is {q['km']:.1f} km away, outside our 7 km delivery area. "
                        "You can pick it up from Alwarpet instead.",
                        [("PICKUP", "Pickup instead"), ("CANCEL", "Cancel order")])]
    ctx.update(lat=str(lat), lng=str(lng), fee=q["fee"], km=round(q["km"], 1))
    return _ask_when(sess)


# ---------------------------------------------------------------- time, payment

def _window_options(now: datetime | None = None) -> list[dict]:
    """ASAP (when open now) plus the next lunch/dinner windows that are
    still open for orders, as list rows."""
    from ..config import DELIVERY_WINDOWS
    now = now or datetime.now(orders.IST)
    rows = []
    if not orders._schedule_closed_reason() and db.get_store_status().get("is_open", True):
        rows.append({"id": "WHEN_NOW", "title": "As soon as possible",
                     "description": "About 45–60 min for delivery, 20 for pickup"})
    for day_off, day_name in ((0, "Today"), (1, "Tomorrow")):
        day = (now + timedelta(days=day_off)).date()
        for w in DELIVERY_WINDOWS:
            ref = datetime(day.year, day.month, day.day, *w["ref"], tzinfo=orders.IST)
            if ref < now + timedelta(minutes=45):
                continue
            iso = ref.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if orders._schedule_closed_reason(iso, w["id"]):
                continue
            rows.append({"id": f"WHEN_{w['id']}_{day.isoformat()}",
                         "title": f"{day_name} {w['label'].split()[0].lower()}"[:24],
                         "description": w["text"]})
    return rows[:10]


def _ask_when(sess: dict) -> list[dict]:
    rows = _window_options()
    if not rows:
        sess["state"] = "root"
        return [text("We're not taking orders for the next two days. Please try again later.")]
    sess["state"] = "when"
    return [{"type": "list", "text": "When would you like it?", "button": "Choose a time",
             "sections": [{"title": "Delivery / pickup time", "rows": rows}]}]


def _set_when(sess: dict, choice: str) -> list[dict] | None:
    from ..config import DELIVERY_WINDOWS
    ctx = sess["ctx"]
    if choice == "WHEN_NOW":
        ctx.update(when="As soon as possible", scheduled_at=None, scheduled_window=None)
    else:
        try:
            _, win_id, day = choice.split("_", 2)
            w = next(x for x in DELIVERY_WINDOWS if x["id"] == win_id.lower())
            d = datetime.fromisoformat(day)
        except (ValueError, StopIteration):
            return None
        ref = datetime(d.year, d.month, d.day, *w["ref"], tzinfo=orders.IST)
        ctx.update(scheduled_at=ref.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   scheduled_window=w["id"])
        ctx["when"] = orders._window_label(w["id"], ctx["scheduled_at"])
    sess["state"] = "payment"
    return [buttons("How would you like to pay?",
                    [("PAY_UPI", "UPI"), ("PAY_COD", "Cash on delivery" if ctx.get("order_type") == "delivery" else "Cash at pickup")])]


# ---------------------------------------------------------------- summary, place

def _totals(sess: dict) -> dict:
    _, subtotal = cart_summary(sess)
    packing = orders.packing_fee_for(subtotal)
    gst = orders.gst_for(subtotal + packing)
    fee = float(sess["ctx"].get("fee") or 0) if sess["ctx"].get("order_type") == "delivery" else 0.0
    return {"subtotal": subtotal, "packing": packing, "gst": gst, "fee": fee,
            "total": round(subtotal + packing + gst + fee, 2)}


def _summary(sess: dict) -> list[dict]:
    ctx = sess["ctx"]
    body, _ = cart_summary(sess)
    t = _totals(sess)
    lines = [body]
    if t["packing"]:
        lines.append(f"Packing — {money(t['packing'])}")
    if t["gst"]:
        lines.append(f"GST — {money(t['gst'])}")
    if ctx.get("order_type") == "delivery":
        lines.append(f"Delivery ({ctx.get('km', '?')} km) — {money(t['fee'])}")
    lines.append(f"*Total: {money(t['total'])}*")
    lines.append("")
    if ctx.get("order_type") == "delivery":
        lines.append(f"📍 {ctx.get('address', '')}")
    else:
        lines.append("📍 Pickup: 34 Murrays Gate Road, Alwarpet")
    lines.append(f"🕒 {ctx.get('when')}")
    lines.append(f"💳 {'UPI' if ctx.get('payment') == 'UPI' else 'Cash'}")
    sess["state"] = "confirm"
    return [buttons("\n".join(lines)[:1000],
                    [("PLACE", "Place order"), ("EDIT", "Change"), ("CANCEL", "Cancel")])]


def _place_order(sess: dict) -> list[dict]:
    ctx = sess["ctx"]
    items = [{"item_id": i, "qty": q} for i, q in sess["cart"].items()]
    try:
        result = orders.create_order(
            phone=sess["wa_id"],
            name=ctx.get("name") or ctx.get("profile_name") or "Customer",
            address=ctx.get("address") if ctx.get("order_type") == "delivery" else None,
            order_type=ctx.get("order_type") or "delivery",
            pincode=ctx.get("pincode"),
            payment_method="upi" if ctx.get("payment") == "UPI" else "cod",
            scheduled_at=ctx.get("scheduled_at"),
            scheduled_window=ctx.get("scheduled_window"),
            items=items,
            lat=ctx.get("lat"),
            lng=ctx.get("lng"),
        )
    except orders.OrderError as e:
        sess["state"] = "root"
        return [text(e.message), catalog_message("Send a new cart from the menu any time.")]
    oid = result["order_id"]
    sess["ctx"]["last_order_id"] = oid
    sess["ctx"]["last_token"] = result.get("tracking_token")
    paying_upi = ctx.get("payment") == "UPI"
    _reset_checkout(sess)
    # The order confirmation itself is the tulsi_order_placed template that
    # orders.create_order sends; here only what that message can't do.
    track = f"{SITE}/track/{result.get('tracking_token') or oid}"
    if paying_upi:
        return [{"type": "cta", "text": f"Order #{oid} is with the kitchen. "
                 f"Pay {money(result['total'])} by UPI to confirm it:",
                 "label": f"Pay {money(result['total'])}", "url": track}]
    return [text(f"Order #{oid} is with the kitchen ✅ We'll message you at every step.")]


def _reset_checkout(sess: dict) -> None:
    sess["cart"] = {}
    sess["state"] = "root"
    for k in ("name", "address", "pincode", "saved_address", "asked_saved", "when",
              "scheduled_at", "scheduled_window", "payment", "order_type", "fee",
              "km", "lat", "lng"):
        sess["ctx"].pop(k, None)


# ---------------------------------------------------------------- track, reorder

def _track(sess: dict) -> list[dict]:
    recent = db.customer_orders(sess["wa_id"], limit=1)
    oid = sess["ctx"].get("last_order_id") or (recent[0]["id"] if recent else None)
    o = db.get_order(oid) if oid else None
    if not o:
        return [text("No order on this number yet."), catalog_message()]
    msg = f"Order #{o['id']} is {STATUS_LABEL.get(o['status'], o['status'])}."
    if o.get("sr_tracking_url"):
        msg += f"\nRider: {o['sr_tracking_url']}"
    return [{"type": "cta", "text": msg, "label": "Track order",
             "url": f"{SITE}/track/{o.get('tracking_token') or o['id']}"}]


def _reorder(sess: dict) -> list[dict]:
    recent = db.customer_orders(sess["wa_id"], limit=1)
    o = db.get_order(recent[0]["id"]) if recent else None
    if not o:
        return [text("No previous order on this number yet."), catalog_message()]
    items = [{"id": it["item_id"], "qty": it["qty"]} for it in o["items"]]
    return _catalog_order(sess, items)


# ---------------------------------------------------------------- entry point

def handle(wa_id: str, incoming: str, profile_name: str | None = None,
           lat: str | None = None, lng: str | None = None,
           catalog_items: list[dict] | None = None,
           address: dict | None = None) -> list[dict]:
    sess = sessions.load(wa_id)
    if profile_name and not sess["ctx"].get("profile_name"):
        sess["ctx"]["profile_name"] = profile_name
    if catalog_items is not None:
        out = _catalog_order(sess, catalog_items)
    elif address is not None:
        out = _on_address_form(sess, address)
    elif lat and lng:
        out = _on_location(sess, lat, lng)
    else:
        out = _route(sess, incoming or "")
    sessions.save(sess)
    return out


def _on_address_form(sess: dict, values: dict) -> list[dict]:
    if sess["state"] != "address":
        return _welcome(sess)
    sess["ctx"]["address"] = _address_from_form(values)[:300]
    sess["ctx"]["pincode"] = (values.get("in_pin_code") or "").strip() or None
    if values.get("name"):
        sess["ctx"]["name"] = values["name"][:60]
    return _ask_location(sess)


def _on_location(sess: dict, lat: str, lng: str) -> list[dict]:
    if sess["state"] in ("location", "address"):
        if sess["state"] == "address" and not sess["ctx"].get("address"):
            sess["ctx"]["address"] = f"Pinned location ({float(lat):.5f}, {float(lng):.5f})"
        return _set_location(sess, lat, lng)
    return [text("Thanks! Send a cart from the menu first, then I'll ask where to deliver."),
            catalog_message()]


GREETINGS = {"HI", "HELLO", "HEY", "HII", "NAMASTE", "VANAKKAM", "START", "ORDER", "MENU",
             "SHOW ME THE MENU", "BACK", "REQUEST_WELCOME"}


def _route(sess: dict, incoming: str) -> list[dict]:
    raw = incoming.strip()
    t = raw.upper()
    state = sess["state"]

    # Commands that work from anywhere
    if t in ("CANCEL", "CLEAR"):
        _reset_checkout(sess)
        return [text("Cancelled. Your cart is empty."), catalog_message("Order again any time:")]
    if t in ("TRACK", "STATUS", "TRACK MY ORDER"):
        return _track(sess)
    if t in ("REORDER", "REORDER MY LAST ORDER"):
        return _reorder(sess)
    if t == "PICKS":
        return [picks_message() or catalog_message()]
    if t == "HELP":
        return [text(HELP_TEXT), catalog_message()]
    if t == "CART":
        return _ask_order_type(sess) if sess["cart"] else [catalog_message("Your cart is empty.")]
    if t == "EDIT":
        sess["state"] = "root"
        return [catalog_message("Change your cart in the menu and send it again.")]
    if t in GREETINGS:
        return _welcome(sess)

    if state == "type":
        if t in ("DELIVERY", "D"):
            sess["ctx"]["order_type"] = "delivery"
            return _ask_address(sess)
        if t in ("PICKUP", "P"):
            sess["ctx"]["order_type"] = "pickup"
            sess["ctx"]["fee"] = 0
            return _ask_when(sess)
        return _ask_order_type(sess)

    if state == "address":
        if t == "SAVED" and sess["ctx"].get("saved_address"):
            sess["ctx"]["address"] = sess["ctx"]["saved_address"]
            return _ask_location(sess)
        if t == "NEWADDR":
            return _ask_address(sess)
        if len(raw) >= 10:  # typed address (non-Indian numbers, or a fallback)
            sess["ctx"]["address"] = raw[:300]
            return _ask_location(sess)
        return _ask_address(sess)

    if state == "location":
        return [text("Tap 📎 → Location → *Send your current location* (or pick the spot on the map)."),
                *_ask_location(sess)]

    if state == "when":
        out = _set_when(sess, t) if t.startswith("WHEN_") else None
        return out or _ask_when(sess)

    if state == "payment":
        if t in ("PAY_UPI", "UPI"):
            sess["ctx"]["payment"] = "UPI"
        elif t in ("PAY_COD", "CASH", "COD"):
            sess["ctx"]["payment"] = "COD"
        else:
            return [buttons("How would you like to pay?", [("PAY_UPI", "UPI"), ("PAY_COD", "Cash")])]
        return _summary(sess)

    if state == "confirm":
        if t in ("PLACE", "YES", "CONFIRM"):
            return _place_order(sess)
        return _summary(sess)

    return _welcome(sess)
