import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from xml.sax.saxutils import escape as xml_escape
from pydantic import BaseModel, Field

from . import catalog, db, faqs, menu, orders, reviews
from .config import (
    ADMIN_TOKEN,
    DELIVERY_ZONES,
    FREE_DELIVERY_ABOVE,
    FREE_DELIVERY_ENABLED,
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

log = logging.getLogger("main")

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


def _group_slug(group: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")
    return slug or "uncategorised"


def group_slugs() -> dict[str, str]:
    """Stable group name -> URL slug map, sourced from the menu itself so the
    category pages, nav links and sitemap can never drift apart."""
    return {g: _group_slug(g) for g in dict.fromkeys(m["group"] for m in menu.load_menu())}


def all_categories() -> list[dict]:
    """Category descriptor list (name, slug, item count) for nav/sitemap."""
    groups: dict[str, list] = {}
    order: list[str] = []
    for m in menu.load_menu():
        g = m["group"]
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append(m)
    return [
        {"name": g, "slug": _group_slug(g), "count": len(groups[g])}
        for g in order
    ]


UPDATES_FILE = Path("data/updates.json")

UPDATE_KIND_LABELS = {
    "instagram": "Instagram", "whatsapp": "WhatsApp status", "update": "Kitchen update",
    "offer": "Offer", "milestone": "Milestone",
}


def _display_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return iso


def load_updates() -> list[dict]:
    """Compilation of Instagram/WhatsApp posts + kitchen announcements for the
    /updates page. File-backed so Mom adds entries without code changes;
    photo/dish references are validated so a typo can't break the page."""
    try:
        raw = json.loads(UPDATES_FILE.read_text())
    except (OSError, ValueError):
        return []
    photos = dish_photo_ids()
    entries = []
    for e in raw.get("entries", []):
        if not e.get("date") or not e.get("title") or not e.get("text"):
            continue
        dishes = [d for d in (e.get("dishes") or []) if menu.get_item(d)]
        entries.append({
            "date": e["date"],
            "date_display": _display_date(e["date"]),
            "kind": e.get("kind") or "update",
            "kind_label": UPDATE_KIND_LABELS.get(e.get("kind") or "update", "Update"),
            "title": e["title"],
            "text": e["text"],
            "photo": e["photo"] if e.get("photo") in photos else None,
            "dishes": [{"id": d, "name": menu.get_item(d)["name"]} for d in dishes],
            "source": e.get("source") or None,
            "source_label": e.get("source_label") or "See the original",
        })
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


CATEGORY_BLURBS: dict[str, str] = {
    "Thalis & Combos": "The whole meal on one plate — phulka, dal, sabzi, rice, curd, salad and a sweet, assembled fresh the moment you order. The North Indian Thali is the restaurant's signature; the Mini Thali is the same idea, half the size.",
    "Parathas & Breads": "Hand-rolled parathas off the tawa, served with curd and pickle. Punjab-style, stuffed parathas, and plain variants that sit beside any sabzi.",
    "Chaats & Snacks": "Made when you order so nothing goes soggy — papdi, dahi puri, vada pav, bhel, pav bhaji and the fried snacks that disappear first.",
    "Sabzi": "Home-style vegetable gravies and dry preparations cooked the same day — dal makhani, paneer butter masala, chole, and seasonal sabzis. Most come in half portions too.",
    "Starters": "Small plates for the table or a light meal — kebabs, tikkas and shallow-fried snacks served with the kitchen's chutneys.",
    "Soups & Rice": "Soups, rice dishes and the lightest things on the menu. Dal-rice and coriander rice are the everyday workhorses.",
    "Chai & Beverages": "Cutting chai, masala chai and thick shakes — the stuff people collect their orders for even when they stay for nothing else.",
    "Desserts": "The sweet that closes every thali, plus the kitchen's desserts. Gajar halwa and kheer show up by season.",
    "Italian": "Pure-veg Italian plates that fit the same kitchen — pastas and baked dishes without the 'fancy restaurant' markup.",
    "Specialities": "The dishes the kitchen is known for beyond the everyday menu — things people cross the city for.",
}


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
    prices = [it["price"] for it in menu.load_menu() if isinstance(it.get("price"), (int, float))]
    price_range = (min(prices), max(prices)) if prices else (60, 350)
    return templates.TemplateResponse(
        request, "landing.html",
        {"picks": picks, "google_stats": google_stats, "google_review_link": GOOGLE_REVIEW_LINK,
         "faqs": faqs.landing_faqs(DELIVERY_ZONES, FREE_DELIVERY_ABOVE, price_range, bool(UPI_VPA)),
         "categories": all_categories(), "latest_updates": load_updates()[:3]},
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
                        "url": f"{SITE_URL}/menu/{it['id'].split('__')[0]}",
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
    for g in groups:
        g["slug"] = _group_slug(g["group"])
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
         "upi_vpa": UPI_VPA, "upi_payee_name": UPI_PAYEE_NAME,
         "free_delivery_above": FREE_DELIVERY_ABOVE,
         "delivery_free_enabled": FREE_DELIVERY_ENABLED,
         "categories": all_categories()},
    )

@app.get("/delivery", response_class=HTMLResponse)
def delivery_page(request: Request):
    return templates.TemplateResponse(
        request, "delivery.html",
        {"zones": DELIVERY_ZONES,
         "faqs": faqs.delivery_faqs(DELIVERY_ZONES, FREE_DELIVERY_ABOVE),
         "categories": all_categories()},
    )


@app.get("/menu/{item_id}", response_class=HTMLResponse)
def menu_item_page(request: Request, item_id: str):
    """One page per dish — each WhatsApp catalog item links here instead of the
    generic /menu. Half-portion ids (`<id>__half`) point at the same dish page."""
    base_id = menu._base_id(item_id) if item_id.endswith(menu.HALF_SUFFIX) else item_id
    item = menu.get_item(base_id)
    if not item:
        raise HTTPException(404, "Dish not found")
    item = dict(item)
    item["photo_id"] = item.get("photo_id") or base_id
    photos = dish_photo_ids()
    has_photo = item["photo_id"] in photos
    day = menu.today()
    available = menu.is_available(base_id, day)
    reason = menu._specialities_reason(item, day)

    # Same-group dishes first (strongest topical link), then pad with popular
    # items from elsewhere so every dish page has real internal links out.
    related = []
    for g in menu.grouped(day):
        if g["group"] == item["group"]:
            related = [it for it in g["items"]
                       if it["id"] != base_id and not it["id"].endswith(menu.HALF_SUFFIX)]
            break
    if len(related) < 4:
        seen = {base_id} | {r["id"] for r in related}
        for g in menu.grouped(day):
            for it in g["items"]:
                if len(related) >= 4:
                    break
                if it["id"] in seen or it["id"].endswith(menu.HALF_SUFFIX):
                    continue
                if it.get("popular"):
                    related.append(it)
                    seen.add(it["id"])
            if len(related) >= 4:
                break

    item_url = f"{SITE_URL}/menu/{base_id}"
    photo_url = f"{SITE_URL}/static/img/dishes/{item['photo_id']}.jpg" if has_photo else ""
    desc = (item.get("description")
            or catalog.FILL_DESCRIPTIONS.get(base_id)
            or f"{item['name']}, a {item['group'].lower()} from Tulsi Foods.")
    wa_link = "https://wa.me/919940062840?text=" + quote(
        f"Hi Tulsi Foods, I'd like to order {item['name']} (₹{item['price']})."
    )

    status_text = "Available now" if available else (reason or "Finished for today")
    ordering = {
        "zones": ", ".join(
            f"{z['name']} up to {z['max_km']:.0f} km — ₹{z['fee']} delivery"
            for z in DELIVERY_ZONES
        ),
        "hours": "Mon–Sat 9 AM – 9 PM, Sun 11 AM – 9 PM",
        "address": "34 Murrays Gate Road, Alwarpet, Chennai 600018",
        "whatsapp": "+91 99400 62840",
        "phone": "+91 99406 21800",
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Menu", "item": f"{SITE_URL}/menu"},
            {"@type": "ListItem", "position": 3, "name": item["group"],
             "item": f"{SITE_URL}/category/{_group_slug(item['group'])}"},
            {"@type": "ListItem", "position": 4, "name": item["name"], "item": item_url},
        ],
    }

    return templates.TemplateResponse(
        request,
        "item.html",
        {"item": item, "has_photo": has_photo, "photo_url": photo_url,
         "available": available, "unavailable_reason": reason,
         "status_text": status_text, "half": item.get("half_price"),
         "related": related, "dish_photos": photos, "wa_link": wa_link,
         "item_url": item_url, "item_description": desc, "ordering": ordering,
         "category_slug": _group_slug(item["group"]),
         "categories": all_categories(),
         "item_schema": _item_product_schema(item, item_url, photo_url, desc, available),
         "breadcrumb_schema": breadcrumb},
    )


def _item_product_schema(item: dict, item_url: str, photo_url: str,
                         desc: str, available: bool) -> dict:
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": item["name"],
        "description": desc,
        "url": item_url,
        "category": item["group"],
        "brand": {"@type": "Brand", "name": "Tulsi Foods"},
        "suitableForDiet": "https://schema.org/VegetarianDiet",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": str(item["price"]),
            "url": item_url,
            "itemCondition": "https://schema.org/NewCondition",
            "availability": ("https://schema.org/InStock" if available
                             else "https://schema.org/OutOfStock"),
        },
    }
    if photo_url:
        schema["image"] = photo_url
    else:
        schema["image"] = f"{SITE_URL}/static/logo.png"
    return schema


@app.get("/track", response_class=HTMLResponse)
def track_landing_page(request: Request):
    """SEO entry point for order tracking. From here a customer finds their
    order by tracking reference or phone and lands on /track/{ref}."""
    return templates.TemplateResponse(request, "track-landing.html", {"categories": all_categories()})


@app.get("/track/{ref}", response_class=HTMLResponse)
def track_page(request: Request, ref: str):
    """Customer tracking page. `ref` is the unguessable tracking token sent in
    the order confirmation; legacy numeric order ids still work (redirected to
    the canonical token URL) so old WhatsApp/SMS links keep resolving."""
    o = db.get_order_by_token(ref) if not ref.isdigit() else db.get_order(int(ref))
    if not o:
        raise HTTPException(404, "Order not found")
    token = o.get("tracking_token") or ref
    if not ref.isdigit():
        return templates.TemplateResponse(
            request, "track.html", {"order_id": o["id"], "tracking_token": token,
                                    "categories": all_categories()}
        )
    return RedirectResponse(f"/track/{token}", status_code=301)


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
            "categories": all_categories(),
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
    return templates.TemplateResponse(request, "bio.html", {"recommendations": recommendations, "categories": all_categories()})


@app.get("/updates", response_class=HTMLResponse)
def updates_page(request: Request):
    """Fresh from the Kitchen — compilation of Instagram/WhatsApp posts and
    kitchen announcements. File-backed (data/updates.json) so new entries land
    without code changes; gives crawlers fresh indexable content to chew on."""
    updates = load_updates()
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Fresh from the Kitchen — Tulsi Foods kitchen updates",
        "url": f"{SITE_URL}/updates",
        "blogPost": [
            {
                "@type": "BlogPosting",
                "headline": u["title"],
                "datePublished": u["date"],
                "articleBody": u["text"],
                **({"image": f"{SITE_URL}/static/img/dishes/{u['photo']}.jpg"} if u["photo"] else {}),
                "author": {"@type": "Organization", "name": "Tulsi Foods"},
            }
            for u in updates
        ],
    }
    return templates.TemplateResponse(
        request, "updates.html",
        {"updates": updates, "categories": all_categories(), "updates_json_ld": json_ld},
    )


@app.get("/updates.xml")
def updates_rss():
    """RSS feed of the same compilation — one more recrawl trigger for bots."""
    items = []
    for u in load_updates():
        link = u["source"] or f"{SITE_URL}/updates"
        items.append(
            f"  <item>\n    <title>{xml_escape(u['title'])}</title>\n"
            f"    <link>{xml_escape(link)}</link>\n"
            f"    <guid>{xml_escape(link)}#{u['date']}</guid>\n"
            f"    <pubDate>{u['date']}T06:00:00+05:30</pubDate>\n"
            f"    <description>{xml_escape(u['text'])}</description>\n  </item>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n'
        f"  <title>Fresh from the Kitchen — Tulsi Foods</title>\n"
        f"  <link>{SITE_URL}/updates</link>\n"
        "  <description>Instagram posts, WhatsApp statuses and kitchen announcements from Tulsi Foods, Mylapore.</description>\n"
        + "\n".join(items) + "\n</channel>\n</rss>"
    )
    return Response(content=body, media_type="application/rss+xml")


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        request, "admin.html", {"groups": menu.grouped(), "hide_nav": True}
    )


@app.get("/kitchen", response_class=HTMLResponse)
def kitchen_page(request: Request):
    # Stripped-down, one-purpose order screen for a kitchen tablet — no tabs,
    # no menu/chat/reviews, just live orders with one big action button each.
    return templates.TemplateResponse(request, "kitchen.html", {"hide_nav": True})


@app.get("/privacy-policy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"categories": all_categories()})


@app.get("/refund-cancellation-policy", response_class=HTMLResponse)
def refund_cancellation_policy_page(request: Request):
    return templates.TemplateResponse(request, "refund-cancellation-policy.html", {"categories": all_categories()})


@app.get("/whatsapp-catalog.csv", response_class=PlainTextResponse)
def whatsapp_catalog_csv():
    return Response(content=catalog.catalog_csv(), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=tulsi-foods-catalog.csv",
    })


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
        "Disallow: /order-actions",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return PlainTextResponse("\n".join(lines))


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    menu_items = [m for m in menu.load_menu() if not m["id"].endswith(menu.HALF_SUFFIX)]
    popular = [m for m in menu_items if m.get("popular")][:8]
    lines = [
        "# Tulsi Foods",
        "",
        "> Pure vegetarian, home-style North Indian restaurant in Mylapore, Chennai. "
        "Run by Kavita Lath since 2015. Thalis, parathas, sabzi, dal and chaat, cooked "
        "to order and delivered direct — no aggregator, no platform fees. 11 years old "
        "as of September 2026.",
        "",
        "- Cuisine: North Indian, pure vegetarian (Jain / no-onion-garlic on request)",
        "- Also known as: Tulasi Foods, Thulasi Restaurant (common misspellings/mishearings of the same restaurant)",
        "- Location: 34 Murrays Gate Road, Alwarpet, Chennai 600018, Tamil Nadu, India",
        "- Hours: Mon–Sat 9 AM–9 PM, Sun 11 AM–9 PM",
        "- Delivery: Mylapore, Alwarpet, Teynampet and nearby areas within ~7 km, by Borzo courier at live rates",
        "- Order: on this website, or WhatsApp at +91 99400 62840",
        "- Phone: +91 99406 21800",
        "- Prices: ₹45–₹400 per dish; most mains available as half portions",
        "",
        "## Pages",
        "",
        f"- [Home]({SITE_URL}/): overview, story, how ordering works",
        f"- [Menu]({SITE_URL}/menu): today's dishes, prices and availability, order online",
        f"- Each dish has its own page, e.g. [Paneer Butter Masala]({SITE_URL}/menu/paneer-butter-masala) — any menu item id at {SITE_URL}/menu/&lt;id&gt;",
        f"- [Track your order]({SITE_URL}/track): look up an order by tracking reference or phone",
        f"- [Delivery]({SITE_URL}/delivery): delivery areas, fees and timing",
        f"- [About]({SITE_URL}/about): the kitchen's story, reviews, and frequently asked questions",
        f"- [Kitchen updates]({SITE_URL}/updates): Instagram posts, WhatsApp statuses and kitchen announcements",
        f"- [Privacy policy]({SITE_URL}/privacy-policy)",
        f"- [Refund &amp; cancellation policy]({SITE_URL}/refund-cancellation-policy)",
        "",
        "## Menu categories",
        "",
    ]
    for cat in all_categories():
        lines.append(f"- {cat['name']} ({cat['count']} items): {SITE_URL}/category/{cat['slug']}")
    lines.append(f"- [All categories]({SITE_URL}/category): the full category index in one page")
    lines += [
        "",
        "## Popular dishes",
        "",
    ]
    for m in popular:
        lines.append(f"- {m['name']} — ₹{m['price']}: {SITE_URL}/menu/{m['id']}")
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
    "/refund-cancellation-policy": "refund-cancellation-policy.html",
    "/track": "track-landing.html",
    "/404": "404.html",
    "/updates": "updates.html",
    "/category": "categories.html",
}


# Sitemap freshness for data-backed pages: lastmod follows the newest of the
# template and its data file, so new entries bump the date without a deploy.
SITEMAP_DATA_FILES = {
    "/updates": UPDATES_FILE,
    "/category": Path("data/menu.json"),
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
        mtimes = []
        template_name = SITEMAP_TEMPLATES.get(path)
        if template_name:
            mtimes.append((template_dir / template_name).stat().st_mtime)
        data_file = SITEMAP_DATA_FILES.get(path)
        if data_file and data_file.exists():
            mtimes.append(data_file.stat().st_mtime)
        if mtimes:
            lastmod_tag = f"\n    <lastmod>{date.fromtimestamp(max(mtimes)).isoformat()}</lastmod>"
        entries.append(f"  <url>\n    <loc>{SITE_URL}{path}</loc>{lastmod_tag}\n  </url>")
    menu_mtime = (Path("data/menu.json")).stat().st_mtime
    menu_items = [m for m in menu.load_menu() if not m["id"].endswith(menu.HALF_SUFFIX)]
    for m in menu_items:
        lastmod_tag = f"\n    <lastmod>{date.fromtimestamp(menu_mtime).isoformat()}</lastmod>"
        entries.append(f"  <url>\n    <loc>{SITE_URL}/menu/{m['id']}</loc>{lastmod_tag}\n  </url>")
    # Category archive pages carry the same freshness as the menu they list.
    for cat in all_categories():
        lastmod_tag = f"\n    <lastmod>{date.fromtimestamp(menu_mtime).isoformat()}</lastmod>"
        entries.append(
            f"  <url>\n    <loc>{SITE_URL}/category/{cat['slug']}</loc>{lastmod_tag}\n  </url>"
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


def _action_page(heading: str) -> HTMLResponse:
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:70px 24px;"
        f"font-size:20px'>{heading}</body></html>"
    )


@app.get("/order-actions/{order_id}/paid", response_class=HTMLResponse)
def order_action_mark_paid(order_id: int, sig: str):
    """One-tap link from Mom's Telegram order alert — no admin login, just a
    signed link (see app/order_actions.py) since she won't use the admin UI."""
    from .order_actions import verify
    if not verify(order_id, "paid", sig):
        raise HTTPException(403, "Invalid link")
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    db.mark_order_paid(order_id)
    return _action_page(f"✅ Order #{order_id} marked as paid.")


@app.get("/order-actions/{order_id}/cancel", response_class=HTMLResponse)
def order_action_cancel(order_id: int, sig: str):
    """One-tap cancel link from Mom's Telegram alert — for orders she cancels
    over a phone call/WhatsApp rather than through Petpooja's own terminal
    (a terminal-side cancel already reaches us via the Petpooja order
    callback and doesn't need this)."""
    from .order_actions import verify
    if not verify(order_id, "cancel", sig):
        raise HTTPException(403, "Invalid link")
    o = db.get_order(order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o["status"] in ("delivered", "cancelled"):
        return _action_page(f"Order #{order_id} is already {o['status']} — nothing to cancel.")
    db.update_order_status(order_id, "cancelled")
    _send_status_whatsapp(o, "cancelled")
    if o.get("petpooja_synced_at"):
        try:
            from .petpooja.client import cancel_order as petpooja_cancel_order, is_configured
            if is_configured():
                petpooja_cancel_order(order_id, "Cancelled by restaurant")
        except Exception:
            log.exception("Petpooja cancel relay failed for order %s", order_id)
    return _action_page(f"❌ Order #{order_id} cancelled.")


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


@app.get("/category", response_class=HTMLResponse)
def category_index(request: Request):
    """Index of all food categories — the parent page the 10 category pages
    hang off, with a card (photo, blurb, count, price range) per category."""
    photos = dish_photo_ids()
    groups = []
    for cat in all_categories():
        items = [m for m in menu.load_menu()
                 if m["group"] == cat["name"] and not m["id"].endswith(menu.HALF_SUFFIX)]
        items.sort(key=lambda m: (not m.get("popular"), m["name"]))
        prices = [float(m["price"]) for m in items if isinstance(m.get("price"), (int, float))]
        photo = next((m["id"] for m in items if m["id"] in photos), None)
        groups.append({"name": cat["name"], "slug": cat["slug"], "count": len(items),
                       "blurb": CATEGORY_BLURBS.get(cat["name"]) or "",
                       "photo": photo,
                       "low": min(prices) if prices else None,
                       "high": max(prices) if prices else None})
    index_url = f"{SITE_URL}/category"
    return templates.TemplateResponse(
        request,
        "categories.html",
        {"groups": groups, "categories": all_categories(),
         "total_items": sum(g["count"] for g in groups), "index_url": index_url,
         "index_json_ld": [
             {"@context": "https://schema.org", "@type": "ItemList",
              "name": "Tulsi Foods menu categories", "url": index_url,
              "numberOfItems": len(groups),
              "itemListElement": [
                  {"@type": "ListItem", "position": i + 1,
                   "name": g["name"], "url": f"{SITE_URL}/category/{g['slug']}"}
                  for i, g in enumerate(groups)]},
             {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL},
                  {"@type": "ListItem", "position": 2, "name": "Categories", "item": index_url}]},
         ]},
    )


@app.get("/category/{slug}", response_class=HTMLResponse)
def category_page(request: Request, slug: str):
    """One SEO page per food category, listing every item in it, all linked
    to their individual dish pages and back to /menu."""
    slugs = group_slugs()
    group = next((g for g, s in slugs.items() if s == slug), None)
    if not group:
        raise HTTPException(404, "Category not found")
    items = [m for m in menu.load_menu() if m["group"] == group and not m["id"].endswith(menu.HALF_SUFFIX)]
    items.sort(key=lambda m: (not m.get("popular"), m["name"]))
    items = [dict(m) for m in items]
    day = menu.today()
    for m in items:
        m["available"] = menu.is_available(m["id"], day)
        m["price"] = float(m["price"])
        m["half"] = m.get("half_price")
    prices = [m["price"] for m in items]
    low, high = (min(prices), max(prices)) if prices else (None, None)
    category_url = f"{SITE_URL}/category/{slug}"
    return templates.TemplateResponse(
        request,
        "category.html",
        {"group": group, "slug": slug, "items": items, "categories": all_categories(),
         "count": len(items), "price_low": low, "price_high": high,
         "blurb": CATEGORY_BLURBS.get(group) or "",
         "bestsellers": [m for m in items if m.get("popular")][:4],
         "category_url": category_url, "dish_photos": dish_photo_ids()},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Branded 404 so a mistyped slug lands on a page with working links out,
    not a bare not-found line. API callers (/api/...) still get clean JSON."""
    if request.url.path.startswith("/api/"):
        raise exc
    return templates.TemplateResponse(request, "404.html", {"categories": all_categories()}, status_code=404)


@app.get("/404", response_class=HTMLResponse)
def not_found_page(request: Request):
    """The 404 page also lives at a real URL (and in the sitemap) so search
    engines can crawl it and customers can return from a bad slug to the site."""
    return templates.TemplateResponse(request, "404.html", {"categories": all_categories()}, status_code=200)


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
    scheduled_window: str | None = None  # lunch | dinner (else None = asap/custom)
    pay_courier_direct: bool = False      # customer pays the delivery rider directly
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
            scheduled_window=order.scheduled_window,
            pay_courier_direct=order.pay_courier_direct,
            items=[{"item_id": it.item_id, "qty": it.qty, "note": it.note} for it in order.items],
        )
        return result
    except orders.OrderError as e:
        raise HTTPException(e.status, e.message)


@app.get("/api/delivery/quote")
def delivery_quote_api(lat: float, lng: float, subtotal: float = 0.0,
                       address: str | None = None):
    """Live courier quote for a dropped pin (Borzo first, zone fallback)."""
    from .delivery.estimate import estimate
    q = estimate(lat, lng, subtotal, address)
    q["free_enabled"] = FREE_DELIVERY_ENABLED
    return q


@app.get("/api/orders/{ref}")
def get_order(ref: str):
    """Public order lookup — token-first for tracking links; numeric order
    ids accepted for internal/bot callers."""
    o = db.get_order_by_token(ref) if not ref.isdigit() else db.get_order(int(ref))
    if not o:
        raise HTTPException(404, "Order not found")
    return o


class PhoneLookupIn(BaseModel):
    phone: str


@app.post("/api/orders/lookup")
def lookup_orders_by_phone(body: PhoneLookupIn):
    """For the /track landing page: which orders belong to this phone number?
    Only returns id, tracking token and a couple of safe fields — the full
    order stays behind the token URL."""
    phone = "".join(ch for ch in body.phone if ch.isdigit())[-10:]
    if len(phone) < 10:
        raise HTTPException(422, "Enter a valid 10-digit phone number")
    return {"orders": db.get_orders_by_phone(f"+91{phone}")}


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
