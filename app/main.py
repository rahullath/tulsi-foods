from datetime import date
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import db, menu, orders, reviews
from .config import (
    ADMIN_TOKEN,
    DELIVERY_ZONES,
    GOOGLE_MAPS_JS_API_KEY,
    GOOGLE_REVIEW_LINK,
    GST_ENABLED,
    GST_RATE,
    PACKING_FEE,
    PACKING_FEE_LARGE_ORDER,
    PACKING_FEE_LARGE_ORDER_THRESHOLD,
)
from .config import UPI_PAYEE_NAME, UPI_VPA
from .delivery.config import PICKUP_LAT, PICKUP_LNG

app = FastAPI(title="Tulsi Foods Direct Ordering", version="0.2.0")

from .webhooks import router as webhook_router
from .qr import router as qr_router, init_qr

app.include_router(webhook_router)
app.include_router(qr_router)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

DISH_PHOTO_DIR = Path("app/static/img/dishes")


def dish_photo_ids() -> set[str]:
    if not DISH_PHOTO_DIR.is_dir():
        return set()
    return {p.stem for p in DISH_PHOTO_DIR.glob("*.jpg")}


# ---- pages ----

# (item_id, tag, short description) — curated, shown on the home page "on the
# stove right now" strip. Falls back to the next entry if one is sold out.
TODAYS_PICKS = [
    ("north-indian-thali", "Today's thali", "Sabzi, dal tadka, phulka, rice and a sweet"),
    ("aloo-paratha", None, "Off the tawa, with curd and pickle"),
    ("paneer-butter-masala", None, "Fresh paneer in tomato and cashew gravy"),
    ("papdi-chat-6pcs", None, "Made when you order so it stays crisp"),
    ("chola-bhatura", None, "Fluffy bhatura with spiced chole"),
    ("dal-makhani", None, "Slow-cooked overnight, finished with cream"),
]


@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    photos = dish_photo_ids()
    picks = []
    for item_id, tag, desc in TODAYS_PICKS:
        item = menu.get_item(item_id)
        if item and menu.is_available(item_id):
            picks.append({**item, "tag": tag, "desc": desc, "has_photo": item_id in photos})
        if len(picks) == 4:
            break
    google_stats = reviews.get_platform_stats().get("google")
    return templates.TemplateResponse(
        request, "landing.html",
        {"picks": picks, "google_stats": google_stats, "google_review_link": GOOGLE_REVIEW_LINK},
    )


def build_menu_schema(groups: list[dict]) -> dict:
    """Menu/MenuSection/MenuItem JSON-LD — mirrors exactly what menu.html
    renders (same groups, same items, same prices), so it always matches
    the visible page rather than drifting into its own thing."""
    return {
        "@context": "https://schema.org",
        "@type": "Menu",
        "name": "Tulsi Foods Menu",
        "url": f"{SITE_URL}/menu",
        "hasMenuSection": [
            {
                "@type": "MenuSection",
                "name": g["group"],
                "hasMenuItem": [
                    {
                        "@type": "MenuItem",
                        "name": it["name"],
                        "offers": {
                            "@type": "Offer",
                            "price": str(it["price"]),
                            "priceCurrency": "INR",
                            "availability": "https://schema.org/InStock" if it["available"]
                            else "https://schema.org/OutOfStock",
                        },
                        "suitableForDiet": "https://schema.org/VegetarianDiet",
                    }
                    for it in g["items"]
                ],
            }
            for g in groups
        ],
    }


@app.get("/mxt0vtchhifb4bxbj27i4aw1em76ra.html", response_class=PlainTextResponse)
def facebook_domain_verification():
    # Meta Business (Facebook) domain ownership verification HTML file.
    return PlainTextResponse("mxt0vtchhifb4bxbj27i4aw1em76ra")


@app.get("/menu", response_class=HTMLResponse)
def menu_page(request: Request):
    groups = menu.grouped()
    return templates.TemplateResponse(
        request,
        "menu.html",
        {"groups": groups, "zones": DELIVERY_ZONES, "dish_photos": dish_photo_ids(),
         "pickup_lat": PICKUP_LAT, "pickup_lng": PICKUP_LNG,
         "google_maps_api_key": GOOGLE_MAPS_JS_API_KEY,
         "menu_schema": build_menu_schema(groups),
         "packing_fee": PACKING_FEE, "packing_fee_large": PACKING_FEE_LARGE_ORDER,
         "packing_fee_threshold": PACKING_FEE_LARGE_ORDER_THRESHOLD,
         "gst_rate": GST_RATE, "gst_enabled": GST_ENABLED,
         "upi_vpa": UPI_VPA, "upi_payee_name": UPI_PAYEE_NAME},
    )

@app.get("/delivery", response_class=HTMLResponse)
def delivery_page(request: Request):
    return templates.TemplateResponse(request, "delivery.html", {"zones": DELIVERY_ZONES})


@app.get("/track/{order_id}", response_class=HTMLResponse)
def track_page(request: Request, order_id: int):
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return templates.TemplateResponse(request, "track.html", {"order_id": order_id})


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {
            "featured_reviews": reviews.list_featured_reviews(),
            "platform_stats": reviews.get_platform_stats(),
            "order_count": reviews.get_order_count_display(),
            "google_review_link": GOOGLE_REVIEW_LINK,
        },
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


@app.get("/kitchen", response_class=HTMLResponse)
def kitchen_page(request: Request):
    # Stripped-down, one-purpose order screen for a kitchen tablet — no tabs,
    # no menu/chat/reviews, just live orders with one big action button each.
    return templates.TemplateResponse(request, "kitchen.html", {})


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
        "Disallow: /kitchen",
        "Disallow: /api/",
        "Disallow: /f",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return PlainTextResponse("\n".join(lines))


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    lines = [
        "# Tulsi Foods",
        "",
        "> Pure vegetarian, home-style North Indian restaurant in Mylapore, Chennai. "
        "Run by Kavita Lath since 2015. Thalis, parathas, sabzi, dal and chaat, cooked "
        "to order and delivered direct — no aggregator, no platform fees.",
        "",
        "- Cuisine: North Indian, pure vegetarian (Jain / no-onion-garlic on request)",
        "- Also known as: Tulasi Foods, Thulasi Restaurant (common misspellings/mishearings of the same restaurant)",
        "- Location: 34 Murrays Gate Road, Alwarpet, Chennai 600018, Tamil Nadu, India",
        "- Hours: Mon–Sat 9 AM–9 PM, Sun 11 AM–9 PM",
        "- Delivery: Mylapore, Alwarpet, Teynampet and nearby areas within ~7 km",
        "- Order: WhatsApp at +91 99400 62840, or the website menu below",
        "- Phone: +91 99406 21800",
        "",
        "## Pages",
        "",
        f"- [Home]({SITE_URL}/): overview, story, how ordering works",
        f"- [Menu]({SITE_URL}/menu): today's dishes, prices and availability, order online",
        f"- [Delivery]({SITE_URL}/delivery): delivery areas, fees and timing",
        f"- [About]({SITE_URL}/about): the kitchen's story, reviews, and frequently asked questions",
        f"- [Privacy policy]({SITE_URL}/privacy-policy)",
    ]
    return PlainTextResponse("\n".join(lines))


# Paths that render HTML but shouldn't be in the public sitemap.
SITEMAP_EXCLUDE = {"/admin", "/kitchen"}

# Optional path -> template file, just to attach a real <lastmod>. A page
# missing here still appears in the sitemap (via route auto-discovery below),
# just without a lastmod — so a new page can never silently fall out of the
# sitemap for want of an entry here.
SITEMAP_TEMPLATES = {
    "/": "landing.html",
    "/menu": "menu.html",
    "/delivery": "delivery.html",
    "/about": "about.html",
    "/bio": "bio.html",
    "/privacy-policy": "privacy.html",
}


@app.get("/sitemap.xml")
def sitemap_xml():
    """Every GET page route that renders HTML, auto-discovered from FastAPI's
    route table — adding a new @app.get(..., response_class=HTMLResponse)
    page is enough for it to show up here, no separate list to remember."""
    template_dir = Path("app/templates")
    paths = sorted({
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.response_class is HTMLResponse
        and "GET" in route.methods
        and "{" not in route.path
        and route.path not in SITEMAP_EXCLUDE
    })
    entries = []
    for path in paths:
        lastmod_tag = ""
        template_name = SITEMAP_TEMPLATES.get(path)
        if template_name:
            mtime = (template_dir / template_name).stat().st_mtime
            lastmod_tag = f"\n    <lastmod>{date.fromtimestamp(mtime).isoformat()}</lastmod>"
        entries.append(f"  <url>\n    <loc>{SITE_URL}{path}</loc>{lastmod_tag}\n  </url>")
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
    """Get saved address(es) for a customer (for checkout pre-fill)."""
    c = db.get_customer(phone)
    if not c:
        return {"exists": False, "address": None, "pincode": None, "name": None, "addresses": []}
    return {"exists": True, "address": c.get("address"), "pincode": c.get("pincode"),
            "name": c.get("name"), "addresses": db.list_customer_addresses(c["id"])}


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


# ---- reviews (admin) ----

class ReviewIn(BaseModel):
    source: str
    quote: str
    author_name: str | None = None
    rating: int | None = None
    proof_url: str | None = None


class FeaturedIn(BaseModel):
    featured: bool


class PlatformStatsIn(BaseModel):
    platform: str
    rating: float | None = None
    review_count: int | None = None


@app.get("/api/admin/reviews")
def admin_list_reviews(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    return {"reviews": reviews.list_reviews()}


@app.post("/api/admin/reviews")
def admin_add_review(body: ReviewIn, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    try:
        rid = reviews.add_review(body.source, body.quote, author_name=body.author_name,
                                 rating=body.rating, proof_url=body.proof_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "id": rid}


@app.delete("/api/admin/reviews/{review_id}")
def admin_delete_review(review_id: int, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    reviews.delete_review(review_id)
    return {"ok": True}


@app.post("/api/admin/reviews/{review_id}/feature")
def admin_feature_review(review_id: int, body: FeaturedIn, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    reviews.set_review_featured(review_id, body.featured)
    return {"ok": True, "featured": body.featured}


@app.get("/api/admin/platform-stats")
def admin_get_platform_stats(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    return {"stats": reviews.get_platform_stats()}


@app.post("/api/admin/platform-stats")
def admin_set_platform_stats(body: PlatformStatsIn, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    try:
        reviews.set_platform_stats(body.platform, body.rating, body.review_count)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


class OrderCountIn(BaseModel):
    count: int


@app.get("/api/admin/order-count")
def admin_get_order_count(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    return {"count": db.get_order_count_estimate()}


@app.post("/api/admin/order-count")
def admin_set_order_count(body: OrderCountIn, x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    try:
        reviews.set_order_count_estimate(body.count)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


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
    """Send status update to customer (WhatsApp template if active, else SMS fallback)."""
    from .notify import notify_status
    notify_status(order, status)


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
    note: str | None = None


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
    scheduled_at: str | None = None
    items: list[OrderItemIn]


@app.post("/api/orders")
def create_order(order: OrderIn):
    try:
        result = orders.create_order(
            phone=order.phone, name=order.name, address=order.address,
            order_type=order.order_type, km=order.km, pincode=order.pincode,
            lat=order.lat, lng=order.lng,
            payment_method=order.payment_method, instructions=order.instructions,
            scheduled_at=order.scheduled_at,
            items=[{"item_id": it.item_id, "qty": it.qty, "note": it.note} for it in order.items],
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


class OrderAddressIn(BaseModel):
    address: str
    pincode: str | None = None
    lat: str | None = None
    lng: str | None = None


@app.post("/api/orders/{order_id}/address")
def edit_order_address(order_id: int, body: OrderAddressIn):
    """Self-service address fix within a few minutes of placing the order."""
    try:
        return orders.edit_address(order_id, body.address, pincode=body.pincode,
                                   lat=body.lat, lng=body.lng)
    except orders.OrderError as e:
        raise HTTPException(e.status, e.message)


@app.get("/api/orders")
def list_orders(limit: int = 20):
    return {"orders": db.recent_orders(limit)}


# ---- admin: today's orders dashboard ----

@app.get("/api/admin/today-orders")
def admin_today_orders(x_admin_token: str | None = Header(None)):
    _check_admin(x_admin_token)
    return {"orders": db.today_orders()}


@app.get("/api/admin/scheduled-orders")
def admin_scheduled_orders(x_admin_token: str | None = Header(None)):
    """All upcoming scheduled orders (any creation date) — the Scheduled
    tab's planning view, since today_orders() only covers today."""
    _check_admin(x_admin_token)
    return {"orders": db.upcoming_scheduled_orders()}


# ---- admin: dispatch (Food Ready) ----

@app.post("/api/admin/orders/{order_id}/dispatch")
def admin_dispatch_order(order_id: int, x_admin_token: str | None = Header(None)):
    """Mom taps 'Food Ready' — triggers rider dispatch via Borzo (primary) or Shiprocket (fallback)."""
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

    # Try Borzo first, fall back to Shiprocket
    from .delivery.config import BORZO_AUTH_TOKEN
    provider = "borzo" if BORZO_AUTH_TOKEN else "shiprocket"

    try:
        if provider == "borzo":
            from .delivery.borzo import create_order as borzo_create, BorzoError
            result = borzo_create(
                order_id=order_id,
                customer_name=o.get("customer_name") or "Customer",
                customer_phone=o.get("customer_phone") or "",
                delivery_address=o["delivery_address"],
                items=o["items"],
                total=o["total"],
                payment_method=o["payment_method"],
                cod_amount=o["total"] if o["payment_method"] == "cod" else 0,
                delivery_lat=o.get("delivery_lat"),
                delivery_lng=o.get("delivery_lng"),
            )
        else:
            from .delivery.shiprocket import dispatch_order, DispatchError
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
            awb=result.get("sr_awb") or result.get("awb_code", ""),
            courier=result.get("sr_courier") or result.get("courier_name", ""),
            tracking_url=result.get("sr_tracking_url") or result.get("tracking_url", ""),
        )
        _send_dispatch_whatsapp(o, result)
        return {"ok": True, "provider": provider, **result}
    except Exception as e:
        raise HTTPException(500, f"Dispatch failed ({provider}): {e}")


def _send_dispatch_whatsapp(order: dict, dispatch: dict) -> None:
    """Send tracking notification to customer (WhatsApp template if active, else SMS fallback)."""
    from .notify import notify_dispatch
    notify_dispatch(order, dispatch)


@app.get("/api/orders/{order_id}/track")
def track_order(order_id: int):
    """Get live tracking info for an order."""
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if not o.get("sr_awb"):
        return {"tracking": None, "status": o["status"]}

    # Try Borzo tracking first (if it's a Borzo order)
    if o["sr_awb"] and o["sr_awb"].startswith("BZ-"):
        try:
            from .delivery.borzo import get_order as borzo_get_order
            borzo_order = borzo_get_order(o["sr_order_id"])
            return {
                "tracking": {
                    "status_text": borzo_order.get("status", ""),
                    "tracking_url": borzo_order.get("tracking_url", o["sr_tracking_url"]),
                },
                "status": o["status"],
            }
        except Exception:
            pass  # fall through

    # Shiprocket tracking (fallback)
    try:
        from .delivery.shiprocket import track_awb, track_order as sr_track_order
        from .delivery.config import SHIPROCKET_CHANNEL_ID
        if o.get("sr_order_id"):
            try:
                tracking = sr_track_order(str(o["sr_order_id"]), SHIPROCKET_CHANNEL_ID)
                return {"tracking": tracking, "status": o["status"]}
            except Exception:
                pass
        tracking = track_awb(o["sr_awb"])
        return {"tracking": tracking, "status": o["status"]}
    except Exception as e:
        return {"tracking": None, "status": o["status"], "error": str(e)}


@app.on_event("startup")
def on_startup():
    db.init_db()
    db.seeded()
    init_qr()
    from .whatsapp import sessions as wa_sessions
    wa_sessions.init_sessions()
