from datetime import date
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import db, menu, orders
from .config import ADMIN_TOKEN, DELIVERY_ZONES, GOOGLE_REVIEW_LINK

app = FastAPI(title="Tulsi Foods Direct Ordering", version="0.2.0")

from .webhooks import router as webhook_router

app.include_router(webhook_router)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

DISH_PHOTO_DIR = Path("app/static/img/dishes")


def dish_photo_ids() -> set[str]:
    if not DISH_PHOTO_DIR.is_dir():
        return set()
    return {p.stem for p in DISH_PHOTO_DIR.glob("*.jpg")}


# ---- pages ----

@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})


@app.get("/menu", response_class=HTMLResponse)
def menu_page(request: Request):
    return templates.TemplateResponse(
        request,
        "menu.html",
        {"groups": menu.grouped(), "zones": DELIVERY_ZONES, "dish_photos": dish_photo_ids()},
    )


RECOMMENDED_DISHES = [
    ("north-indian-thali", "Bestseller"),
    ("chola-bhatura", "Must try"),
    ("paneer-butter-masala", "Trending"),
    ("pav-bhaji", None),
    ("sabudana-vada-2pcs", None),
    ("dal-makhani", None),
]


@app.get("/bio", response_class=HTMLResponse)
def bio_page(request: Request):
    photos = dish_photo_ids()
    recommendations = []
    for item_id, tag in RECOMMENDED_DISHES:
        item = menu.get_item(item_id)
        if item:
            recommendations.append({**item, "tag": tag, "has_photo": item_id in photos})
    return templates.TemplateResponse(request, "bio.html", {"recommendations": recommendations})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        request, "admin.html", {"groups": menu.grouped()}
    )


@app.get("/privacy-policy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


# ---- SEO: verification, robots, sitemap ----

SITE_URL = "https://tulsifoods.app"


@app.get("/googlee69732d81b8747c7.html", response_class=PlainTextResponse)
def google_site_verification():
    # Google Search Console domain ownership verification (HTML file method).
    return PlainTextResponse("google-site-verification: googlee69732d81b8747c7.html")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /admin",
        "Disallow: /api/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return PlainTextResponse("\n".join(lines))


@app.get("/sitemap.xml")
def sitemap_xml():
    template_dir = Path("app/templates")
    pages = [
        ("/", "landing.html"),
        ("/menu", "menu.html"),
        ("/bio", "bio.html"),
        ("/privacy-policy", "privacy.html"),
    ]
    entries = []
    for path, template_name in pages:
        mtime = (template_dir / template_name).stat().st_mtime
        lastmod = date.fromtimestamp(mtime).isoformat()
        entries.append(
            f"  <url>\n    <loc>{SITE_URL}{path}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )
    return Response(content=body, media_type="application/xml")


# ---- menu API ----

@app.get("/api/menu")
def api_menu(day: str | None = None):
    return {"date": menu.today(day), "groups": menu.grouped(day)}


@app.get("/api/delivery")
def api_delivery(km: float, subtotal: float = 0.0):
    q = orders.delivery_fee(km, subtotal)
    if not q:
        return {"zone": "outside", "fee": None, "min_order": None}
    return {"zone": q["zone"], "fee": q["fee"], "min_order": q["min_order"]}


@app.get("/api/delivery/check")
def api_delivery_check(pincode: str):
    """Check if a pincode is serviceable by Shiprocket Quick."""
    result = orders.check_pincode_serviceable(pincode)
    return result


@app.get("/api/customer/{phone}")
def api_customer_info(phone: str):
    """Get saved address/pincode for a customer (for checkout pre-fill)."""
    c = db.get_customer(phone)
    if not c:
        return {"exists": False, "address": None, "pincode": None, "name": None}
    return {"exists": True, "address": c.get("address"), "pincode": c.get("pincode"),
            "name": c.get("name")}


# ---- availability (admin) ----

def _check_admin(token: str | None):
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


class AvailabilityIn(BaseModel):
    available_ids: list[str] = Field(default_factory=list)
    unavailable_ids: list[str] = Field(default_factory=list)


@app.get("/api/admin/availability")
def admin_availability(day: str | None = None, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    available = db.get_available_ids(day)
    return {"date": day, "available_ids": sorted(available), "last_day": db.last_available_day()}


@app.post("/api/admin/availability")
def admin_set_availability(body: AvailabilityIn, day: str | None = None,
                           x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    db.set_availability(day, body.available_ids, body.unavailable_ids)
    return {"date": day, "ok": True}


@app.post("/api/admin/availability/repeat-yesterday")
def admin_repeat_yesterday(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    last = db.last_available_day()
    if not last:
        raise HTTPException(400, "No previously saved day to copy")
    today = date.today().isoformat()
    n = db.copy_availability(last, today)
    return {"ok": True, "copied_from": last, "copied_items": n}


# ---- daily specials (admin) ----

class SpecialIn(BaseModel):
    item_name: str
    price: float


@app.get("/api/admin/special")
def admin_get_special(day: str | None = None, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    special = db.get_special(day)
    return {"date": day, "special": special}


@app.post("/api/admin/special")
def admin_set_special(body: SpecialIn, day: str | None = None,
                      x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    db.set_special(day, body.item_name, body.price)
    return {"date": day, "ok": True, "special": body.model_dump()}


@app.delete("/api/admin/special")
def admin_clear_special(day: str | None = None, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    day = menu.today(day)
    db.clear_special(day)
    return {"date": day, "ok": True}


# ---- WhatsApp conversations (admin) ----

class HumanIn(BaseModel):
    human: bool


# ---- admin: order state machine ----

class StatusIn(BaseModel):
    status: str


VALID_TRANSITIONS = {
    "new": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["out_for_delivery", "delivered"],  # delivered for pickup
    "out_for_delivery": ["delivered"],
}


@app.post("/api/admin/orders/{order_id}/status")
def admin_update_order_status(order_id: int, body: StatusIn,
                              x_admin_token: str | None = Header(None)):
    """Advance order to next state. Sends WhatsApp notification to customer."""
    _check_admin(x_admin_token)
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    current = o["status"]
    target = body.status
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(400, f"Cannot move from '{current}' to '{target}'. Allowed: {allowed}")
    db.update_order_status(order_id, target)
    _send_status_whatsapp(o, target)
    return {"ok": True, "order_id": order_id, "from": current, "to": target}


def _send_status_whatsapp(order: dict, status: str) -> None:
    """Send status update to customer. Uses template if available, falls back to text."""
    try:
        from .whatsapp import client
        phone = order.get("customer_phone", "")
        if not phone:
            return
        oid = order["id"]
        # Map status → template name + params
        templates = {
            "preparing": ("order_preparing", [{"type": "text", "text": str(oid)}]),
            "ready": (
                ("order_out_for_delivery" if order["order_type"] == "delivery" else "order_preparing"),
                [{"type": "text", "text": str(oid)},
                 {"type": "text", "text": order.get("sr_courier") or "the restaurant"},
                 {"type": "text", "text": ""}],
            ),
            "delivered": ("order_delivered", []),
        }
        if status in templates:
            tpl_name, params = templates[status]
            try:
                client.send_template(phone, tpl_name, "en", params)
                return
            except Exception:
                pass  # template not approved yet, fall back to text
        # Fallback: plain text
        if status == "preparing":
            msg = f"Order #{oid} is being cooked now. We'll tell you when it leaves the kitchen."
        elif status == "ready":
            if order["order_type"] == "pickup":
                msg = f"Order #{oid} is ready for pickup! Come and collect."
            else:
                msg = f"Order #{oid} is ready! Dispatching shortly."
        elif status == "delivered":
            msg = (
                f"Order #{oid} delivered. Enjoy your meal 🙏 If anything wasn't right, reply here and we'll fix it.\n\n"
                f"If you did enjoy it, an honest Google review helps our small kitchen a lot: {GOOGLE_REVIEW_LINK}"
            )
        elif status == "cancelled":
            msg = f"Order #{oid} has been cancelled."
        else:
            return
        client.send_text(phone, msg)
    except Exception:
        pass  # non-fatal


@app.get("/api/admin/conversations")
def admin_conversations(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    from .whatsapp import sessions as wa_sessions
    return {"conversations": wa_sessions.all_sessions()}


@app.post("/api/admin/conversations/{wa_id}/human")
def admin_conversation_human(wa_id: str, body: HumanIn,
                             x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    from .whatsapp import sessions as wa_sessions
    wa_sessions.set_human(wa_id, body.human)
    return {"wa_id": wa_id, "human": body.human, "ok": True}


# ---- orders ----

class OrderItemIn(BaseModel):
    item_id: str
    qty: float = Field(gt=0)


class OrderIn(BaseModel):
    phone: str
    name: str
    address: str | None = None
    order_type: str = "delivery"  # delivery | pickup
    km: float | None = None
    pincode: str | None = None
    lat: str | None = None
    lng: str | None = None
    payment_method: str = "cod"   # cod | upi
    instructions: str | None = None
    items: list[OrderItemIn]


@app.post("/api/orders")
def create_order(order: OrderIn):
    try:
        result = orders.create_order(
            phone=order.phone, name=order.name, address=order.address,
            order_type=order.order_type, km=order.km, pincode=order.pincode,
            lat=order.lat, lng=order.lng,
            payment_method=order.payment_method, instructions=order.instructions,
            items=[{"item_id": it.item_id, "qty": it.qty} for it in order.items],
        )
        return result
    except orders.OrderError as e:
        raise HTTPException(e.status, e.message)


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return o


@app.get("/api/orders")
def list_orders(limit: int = 20):
    return {"orders": db.recent_orders(limit)}


# ---- admin: today's orders dashboard ----

@app.get("/api/admin/today-orders")
def admin_today_orders(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    return {"orders": db.today_orders()}


# ---- admin: dispatch (Food Ready) ----

@app.post("/api/admin/orders/{order_id}/dispatch")
def admin_dispatch_order(order_id: int, x_admin_token: str | None = Header(None)):
    """Mom taps 'Food Ready' — triggers Shiprocket rider dispatch."""
    _check_admin(x_admin_token)
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o["order_type"] != "delivery":
        raise HTTPException(400, "Cannot dispatch pickup orders")
    if o["status"] != "ready":
        raise HTTPException(400, f"Order must be ready before booking a rider (currently {o['status']})")
    if not o.get("delivery_address") or not o.get("delivery_pincode"):
        raise HTTPException(400, "Order missing delivery address or pincode")
    try:
        from .delivery.shiprocket import dispatch_order
        result = dispatch_order(
            order_id=order_id,
            customer_name=o.get("customer_name") or "Customer",
            customer_phone=o.get("customer_phone") or "",
            delivery_address=o["delivery_address"],
            delivery_pincode=o["delivery_pincode"],
            items=o["items"],
            total=o["total"],
            payment_method=o["payment_method"],
            delivery_lat=o.get("delivery_lat"),
            delivery_lng=o.get("delivery_lng"),
        )
        db.update_order_dispatch(
            order_id=order_id,
            sr_order_id=result["sr_order_id"],
            awb=result["awb_code"],
            courier=result["courier_name"],
            tracking_url=result["tracking_url"],
        )
        # Push WhatsApp notification to customer
        _send_dispatch_whatsapp(o, result)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(500, f"Dispatch failed: {e}")


def _send_dispatch_whatsapp(order: dict, dispatch: dict) -> None:
    """Send tracking notification to customer via WhatsApp."""
    try:
        from .whatsapp import client
        phone = order.get("customer_phone", "")
        if not phone:
            return
        msg = (
            f"Your order #{order['id']} is on its way! 🛵\n"
            f"Courier: {dispatch['courier_name']}\n"
            f"Track: {dispatch['tracking_url']}\n"
            f"We'll update you when it's delivered."
        )
        client.send_text(phone, msg)
    except Exception:
        pass  # non-fatal


@app.get("/api/orders/{order_id}/track")
def track_order(order_id: int):
    """Get live tracking info for an order."""
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if not o.get("sr_awb"):
        return {"tracking": None, "status": o["status"]}
    try:
        from .delivery.shiprocket import track_awb, track_order as sr_track_order
        from .delivery.config import SHIPROCKET_CHANNEL_ID
        # Prefer order-based tracking (richer response with track_url)
        if o.get("sr_order_id"):
            try:
                tracking = sr_track_order(str(o["sr_order_id"]), SHIPROCKET_CHANNEL_ID)
                return {"tracking": tracking, "status": o["status"]}
            except Exception:
                pass  # fall through to AWB-based
        tracking = track_awb(o["sr_awb"])
        return {"tracking": tracking, "status": o["status"]}
    except Exception as e:
        return {"tracking": None, "status": o["status"], "error": str(e)}


@app.on_event("startup")
def on_startup():
    db.init_db()
    db.seeded()
    from .whatsapp import sessions as wa_sessions
    wa_sessions.init_sessions()
