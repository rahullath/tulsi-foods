# Exact-text edits for the clean base. Each (file, old, new) must match.
# Defaults describe a fictional "Sample Kitchen" so the app runs out of the box.

SITE = "business.site_url"

RULES += [
    # ---------------- business identity defaults
    ("app/business.py", 'Defaults describe the Tulsi Foods kitchen, so nothing changes until a value is\noverridden.', 'Defaults describe a fictional sample kitchen so the app runs out of the box;\nset the BIZ_* variables to describe yours.'),
    ("app/business.py", """'+919940621800' -> '+91 99406 21800' (Indian mobile grouping).""", """'+919876543210' -> '+91 98765 43210' (Indian mobile grouping)."""),
    ("app/business.py", '_env("NAME", "Tulsi Foods")', '_env("NAME", "Sample Kitchen")'),
    ("app/business.py", '    instagram = _env("INSTAGRAM", "tulsi.foods_chennai")\n    email = _env("EMAIL", "tulsifoodsco@gmail.com")',
     '    instagram = _env("INSTAGRAM", "")\n    email = _env("EMAIL", "hello@example.com")\n    site_url = _env("SITE_URL", "https://example.com").rstrip("/")\n    tagline = _env("TAGLINE", "Home-style food, cooked to order")\n    about = _env("ABOUT", "Tell customers who you are and how you cook. Set BIZ_ABOUT, or edit app/templates/about.html.")'),
    ("app/business.py", '_env("STREET_NO", "34")', '_env("STREET_NO", "12")'),
    ("app/business.py", '_env("STREET", "Murrays Gate Road")', '_env("STREET", "Market Road")'),
    ("app/business.py", '_env("LOCALITY", "Alwarpet")', '_env("LOCALITY", "Old Town")'),
    ("app/business.py", '_env("CITY", "Chennai")', '_env("CITY", "Sampletown")'),
    ("app/business.py", '_env("PINCODE", "600018")', '_env("PINCODE", "000000")'),
    ("app/business.py", '_env("STATE", "Tamil Nadu")', '_env("STATE", "Sample State")'),
    ("app/business.py", '_env("PHONE", "+919940621800")', '_env("PHONE", "+919876543210")'),
    ("app/business.py", '_env("CONTACT_WHATSAPP", "+919940062840")', '_env("CONTACT_WHATSAPP", "+919876543211")'),
    ("app/business.py", """Without the country code: '99406 21800'.""", """Without the country code: '98765 43210'."""),
    ("app/business.py", """Ten digits, no spaces: '9940621800'.""", """Ten digits, no spaces: '9876543210'."""),
    ("app/business.py", """'34 Murrays Gate Road, Alwarpet'""", """'12 Market Road, Old Town'"""),
    ("app/business.py", """'34 Murrays Gate Road, Alwarpet, Chennai 600018'""", """'12 Market Road, Old Town, Sampletown 000000'"""),
    ("app/business.py", """'34, Murrays Gate Road, Alwarpet, Chennai 600018'""", """'12, Market Road, Old Town, Sampletown 000000'"""),
    ("app/business.py", """'34, Murrays Gate Road, Alwarpet, Chennai'""", """'12, Market Road, Old Town, Sampletown'"""),
    ("app/business.py", """'34, Murrays Gate Road, Alwarpet' (schema.org streetAddress)""", """'12, Market Road, Old Town' (schema.org streetAddress)"""),
    ("app/business.py", """Courier form: '34, Murrays Gate Road, Alwarpet, Chennai, 600018, Tamil Nadu, India'""", """Courier form: '12, Market Road, Old Town, Sampletown, 000000, Sample State, India'"""),

    # ---------------- config
    ("app/config.py", 'DB_FILE = DATA_DIR / "tulsi.db"', 'DB_FILE = DATA_DIR / "kitchen.db"'),
    ("app/config.py", 'ADMIN_TOKEN = os.environ.get("TULSI_ADMIN_TOKEN", "tulsi")',
     '# The kitchen screen password. If unset, a random one is generated for this run\n# and printed at startup, so there is never a well-known default.\nimport secrets as _secrets\nADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or _secrets.token_urlsafe(12)\nif not os.environ.get("ADMIN_TOKEN"):\n    print(f"[config] ADMIN_TOKEN not set; using a temporary one for this run: {ADMIN_TOKEN}")'),
    ("app/config.py", 'WHATSAPP_ORDER_NUMBER = os.environ.get("WHATSAPP_ORDER_NUMBER", "919361394084")', 'WHATSAPP_ORDER_NUMBER = os.environ.get("WHATSAPP_ORDER_NUMBER", "")'),
    ("app/config.py", 'WHATSAPP_ORDER_DISPLAY = os.environ.get("WHATSAPP_ORDER_DISPLAY", "+91 93613 94084")', 'WHATSAPP_ORDER_DISPLAY = os.environ.get("WHATSAPP_ORDER_DISPLAY", "")'),
    ("app/config.py", 'META_BUSINESS_ID = os.environ.get("META_BUSINESS_ID", "714196232763226")', 'META_BUSINESS_ID = os.environ.get("META_BUSINESS_ID", "")'),
    ("app/config.py", 'WHATSAPP_CATALOG_ID = os.environ.get("WHATSAPP_CATALOG_ID", "1768879374330631")', 'WHATSAPP_CATALOG_ID = os.environ.get("WHATSAPP_CATALOG_ID", "")'),
    ("app/config.py", 'WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "tulsi_verify")', 'WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")'),
    ("app/config.py", 'UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", "Tulsi Foods")', 'UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", _biz.name)'),
    ("app/config.py", 'UPI_TXN_NOTE = os.environ.get("UPI_TXN_NOTE", "Tulsi Foods order payment")', 'UPI_TXN_NOTE = os.environ.get("UPI_TXN_NOTE", f"{_biz.name} order payment")'),
    ("app/config.py", 'TULSI_ADMIN_URL = os.environ.get("TULSI_ADMIN_URL", "https://tulsifoods.app")', 'SITE_URL = os.environ.get("SITE_URL", _biz.site_url)'),
    ("app/config.py", '    {"areas": "Mylapore, Alwarpet, Royapettah", "ride": "15–25 min ride"},\n    {"areas": "Teynampet, Nandanam, R.A. Puram", "ride": "20–30 min ride"},\n    {"areas": "Adyar, T. Nagar, Egmore", "ride": "30–40 min ride"},',
     '    {"areas": "Closest neighbourhoods", "ride": "15–25 min ride"},\n    {"areas": "Nearby neighbourhoods", "ride": "20–30 min ride"},\n    {"areas": "Farther neighbourhoods", "ride": "30–40 min ride"},'),
]

# ---------------- backend: functional identity strings -> business config
RULES += [
    ("app/catalog.py", 'SITE_URL = "https://tulsifoods.app"', 'from .business import business\n\nSITE_URL = business.site_url'),
    ("app/catalog.py", 'BRAND = "Tulsi Foods"', 'BRAND = business.name'),
    ("app/catalog.py", ' Pure vegetarian, from the Tulsi Foods kitchen in Mylapore, Chennai."', ' From the {BRAND} kitchen in {business.city}."'),
    ("app/catalog.py", "desc = f\"Home-style {item.get('group') or 'North Indian'} dish, cooked to order.\"", "desc = f\"A {(item.get('group') or 'house').lower()} dish, cooked to order.\""),
    ("app/notify.py", 'return f"https://tulsifoods.app/track/{order.get(\'tracking_token\') or order[\'id\']}"', 'return f"{business.site_url}/track/{order.get(\'tracking_token\') or order[\'id\']}"'),
    ("app/notify.py", 'text = (f"Tulsi Foods: your rider is booked', 'text = (f"{business.name}: your rider is booked'),
    ("app/wa_link.py", 'SITE = "https://tulsifoods.app"', 'from .business import business\n\nSITE = business.site_url'),
    ("app/qr.py", 'QR_TARGET = os.getenv("QR_TARGET", "https://tulsifoods.app/menu")', 'from .business import business\n\nQR_TARGET = os.getenv("QR_TARGET", f"{business.site_url}/menu")'),
    ("app/whatsapp/client.py", '"footer": {"text": "Tulsi Foods"},', '"footer": {"text": business.name},'),
    ("app/whatsapp/client.py", '"View menu", "https://tulsifoods.app/menu")', '"View menu", f"{business.site_url}/menu")'),
    ("app/whatsapp/conversation.py", 'SITE = "https://tulsifoods.app"', 'SITE = business.site_url'),
    ("app/whatsapp/conversation.py", '"header": "Popular at Tulsi Foods",', '"header": f"Popular at {business.name}"[:60],'),
    ("app/whatsapp/conversation.py", 'hello = f"Namaste{\' \' + name if name else \'\'}! Welcome to Tulsi Foods, Mylapore 🍛"', 'hello = f"Hello{\' \' + name if name else \'\'}! Welcome to {business.name} 🍛"'),
    ("app/whatsapp/conversation.py", 'out.append(text(hello + "\\nPure veg, home-style North Indian. Order right here, "\n                        "no app and no platform fees."))', 'out.append(text(hello + f"\\n{business.tagline}. Order right here, no app needed."))'),
    ("app/whatsapp/conversation.py", '"You can pick it up from Alwarpet instead.",', 'f"You can pick it up from {business.locality} instead.",'),
    ("app/delivery/borzo.py", 'return "Tulsi Foods: " + ", ".join(parts)', 'return f"{business.name}: " + ", ".join(parts)'),
    ("app/delivery/borzo.py", '"contact_person": {"phone": PICKUP_PHONE, "name": "Tulsi Foods"},', '"contact_person": {"phone": PICKUP_PHONE, "name": business.name},'),
    ("app/delivery/borzo.py", 'if "chennai" not in addr.lower():\n        addr = f"{addr}, Chennai, Tamil Nadu, India"', 'if business.city.lower() not in addr.lower():\n        addr = f"{addr}, {business.city}, {business.state}, {business.country}"'),
    ("app/delivery/porter.py", '"pickup_name": "Tulsi Foods",', '"pickup_name": business.name,'),
    ("app/delivery/shiprocket.py", 'headers = {"User-Agent": "tulsi-foods-ordering/1.0"}', 'headers = {"User-Agent": f"{business.name} ordering/1.0"}'),
    ("app/delivery/shiprocket.py", 'queries = [f"{address}, {pincode}, Chennai, Tamil Nadu, India", f"{pincode}, Chennai, Tamil Nadu, India"]', 'place = f"{business.city}, {business.state}, {business.country}"\n    queries = [f"{address}, {pincode}, {place}", f"{pincode}, {place}"]'),
    ("app/delivery/shiprocket.py", '"billing_city": "Chennai",\n        "billing_state": "Tamil Nadu",\n        "billing_country": "India",', '"billing_city": business.city,\n        "billing_state": business.state,\n        "billing_country": business.country,'),
    ("app/geo.py", 'query = ", ".join(p for p in (address, pincode, "Chennai, Tamil Nadu, India") if p)', 'query = ", ".join(p for p in (address, pincode, f"{business.city}, {business.state}, {business.country}") if p)'),
    ("app/geo.py", 'headers = {"User-Agent": "tulsi-foods-ordering/1.0 (tulsifoods.app)"}', 'headers = {"User-Agent": f"{business.name} ordering/1.0 ({business.site_url})"}'),
    ("app/geo.py", '(f"{pincode}, Chennai, India" if pincode else "", False)', '(f"{pincode}, {business.city}, {business.country}" if pincode else "", False)'),
    ("app/petpooja/config.py", 'PETPOOJA_RES_NAME = "Tulsi Foods"', 'PETPOOJA_RES_NAME = business.name'),
    ("app/kitchen_alerts.py", 'f"👩‍🍳 From the Tulsi kitchen:\\n{text.strip()[:3000]}"', 'f"👩‍🍳 From the {business.name} kitchen:\\n{text.strip()[:3000]}"'),
    ("app/kitchen_alerts.py", 'kitchen_link = f"https://tulsifoods.app/kitchen/o/{oid}"', 'kitchen_link = f"{business.site_url}/kitchen/o/{oid}"'),
    ("app/orders.py", 'from .config import TULSI_ADMIN_URL', 'from .config import SITE_URL'),
    ("app/orders.py", '{TULSI_ADMIN_URL}/webhook/petpooja', '{SITE_URL}/webhook/petpooja'),
    ("app/telegram.py", 'from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TULSI_ADMIN_URL', 'from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SITE_URL'),
    ("app/reviews.py", 'if platform not in ("swiggy", "zomato", "google"):', 'if platform not in ("google",):'),
    ("app/reviews.py", '    "swiggy": "Swiggy",\n    "zomato": "Zomato",\n', ''),
    ("app/third_party_ratings.py", '"""Swiggy\'s per-dish ratings, shown on our dish pages as Swiggy\'s ratings.', '"""Per-dish ratings from another site, shown on dish pages as that site\'s ratings.'),
    ("app/third_party_ratings.py", 'Refresh app/swiggy_ratings.json from the Swiggy menu page\nnow and then;', 'Put ratings in app/external_ratings.json;'),
    ("app/third_party_ratings.py", '"swiggy_ratings.json"', '"external_ratings.json"'),
    ("app/third_party_ratings.py", 'def swiggy(item_id: str)', 'def external(item_id: str)'),
    ("app/main.py", 'templates.env.globals["swiggy_rating"] = third_party_ratings.swiggy', 'templates.env.globals["external_rating"] = third_party_ratings.external'),
    ("app/main.py", 'app = FastAPI(title="Tulsi Foods Direct Ordering", version="0.2.0")', 'app = FastAPI(title="Direct ordering", version="0.2.0")'),
    ("app/main.py", 'SITE_URL = "https://tulsifoods.app"', 'SITE_URL = biz.site_url'),
    ("app/main.py", 'filename=tulsi-foods-catalog.csv', 'filename=catalog.csv'),
    ("app/main.py", '"name": "Tulsi Kitchen", "short_name": "Kitchen"', '"name": f"{biz.name} kitchen", "short_name": "Kitchen"'),
    ("app/main.py", '"name": "Tulsi Foods Menu",', '"name": f"{biz.name} menu",'),
    ("app/main.py", '"brand": {"@type": "Brand", "name": "Tulsi Foods"},', '"brand": {"@type": "Brand", "name": biz.name},'),
    ("app/main.py", '"tn": f"Tulsi Foods order {order_id}", "tr": f"TF{order_id}"', '"tn": f"{biz.name} order {order_id}", "tr": f"ORD{order_id}"'),
    ("app/main.py", '"name": "Tulsi Foods menu categories", "url": index_url,', '"name": f"{biz.name} menu categories", "url": index_url,'),
    ("app/main.py", 'or f"{item[\'name\']}, a {item[\'group\'].lower()} from Tulsi Foods.")', 'or f"{item[\'name\']}, a {item[\'group\'].lower()} from {biz.name}.")'),
    ("app/main.py", 'f"Hi Tulsi Foods, I\'d like to order {item[\'name\']} (₹{item[\'price\']})."', 'f"Hi {biz.name}, I\'d like to order {item[\'name\']} (₹{item[\'price\']})."'),
]

# ---------------- comment and message wording
for g in ("**/*.py", "**/*.js", "**/*.md"):
    REGEX_RULES += [
        (g, r"\bMom's\b", "the owner's"), (g, r"\bMom\b", "the owner"),
        (g, r"\bmom's\b", "the owner's"), (g, r"\bmom\b", "the owner"),
        (g, r"\btulsi_(?=[a-z])", ""),
        (g, r"tell Rahul", "tell the admin"),
    ]

IMPORTS.update({
    "app/delivery/borzo.py": "from ..business import business",
    "app/delivery/porter.py": "from ..business import business",
    "app/delivery/shiprocket.py": "from ..business import business",
    "app/geo.py": "from .business import business",
    "app/petpooja/config.py": "from ..business import business",
    "app/notify.py": "from .business import business",
    "app/kitchen_alerts.py": "from .business import business",
    "app/whatsapp/client.py": "from ..business import business",
})

RULES += [
    ("app/business.py", '    site_url = _env("SITE_URL", "https://example.com").rstrip("/")',
     '    site_url = _env("SITE_URL", "https://example.com").rstrip("/")\n    service_areas = [a.strip() for a in _env("SERVICE_AREAS", "").split(",") if a.strip()]'),
    ("app/main.py", '"name": f"{a}, Chennai"}', '"name": f"{a}, {biz.city}"}'),
]

RULES += [
    # main.py content
    ("app/main.py", 'Falls back to "<Group> at Tulsi Foods, Mylapore".', 'Falls back to "<Group> at <business name>".'),
    ("app/main.py", 'CATEGORY_HERO_ALT = {\n    "thalis-combos": "North Indian Thali box labelled compartment-wise: curd, jeera rice, gulab jamun, veg kofta, dal tadka, phulkas, salad and mix veg — Tulsi Foods, Mylapore",\n}', 'CATEGORY_HERO_ALT: dict[str, str] = {}'),
    ("app/main.py", 'f"{group} at Tulsi Foods, Mylapore")}', 'f"{group} at {business.name}")}'),
    ("app/main.py", '"name": "Fresh from the Kitchen — Tulsi Foods kitchen updates",', '"name": f"Fresh from the Kitchen — {biz.name} kitchen updates",'),
    ("app/main.py", '"author": {"@type": "Organization", "name": "Tulsi Foods"},', '"author": {"@type": "Organization", "name": biz.name},'),
    ("app/main.py", 'f"  <title>Fresh from the Kitchen — Tulsi Foods</title>\\n"', 'f"  <title>Fresh from the Kitchen — {biz.name}</title>\\n"'),
    ("app/main.py", '"  <description>Instagram posts, WhatsApp statuses and kitchen announcements from Tulsi Foods, Mylapore.</description>\\n"', 'f"  <description>Kitchen announcements from {biz.name}, {biz.locality}.</description>\\n"'),
    ("app/main.py", '        f"> Pure vegetarian, home-style North Indian kitchen on {biz.street}, {biz.locality} "\n        "(Mylapore side), Chennai. Run by Kavita Lath since 2015. Thalis, parathas, sabzi, "\n        "dal and chaat, cooked to order and delivered direct from the kitchen.",',
     '        f"> {biz.tagline}. {biz.name} is on {biz.street}, {biz.locality}, {biz.city}, "\n        "cooked to order and delivered direct from the kitchen.",'),
    ("app/main.py", '        "- Cuisine: North Indian, pure vegetarian. Jain and no-onion-garlic on request.",\n        "- Also known as: Tulsi Restaurant, Tulasi Foods, Thulasi Restaurant (same kitchen, different spellings)",\n', ''),
    ("app/main.py", '        f"- Delivery: fixed fee by distance from the kitchen: {fees}. Areas: "\n        + ", ".join(seo_aliases.NEARBY_AREAS) + ". Riders are booked with Porter.",',
     '        f"- Delivery: fixed fee by distance from the kitchen: {fees}."\n        + (" Areas: " + ", ".join(seo_aliases.NEARBY_AREAS) + "." if seo_aliases.NEARBY_AREAS else ""),'),
    ("app/main.py", 'f"- Hours: {faqs._open_text()}. On Mondays, orders open at 2 PM.",', 'f"- Hours: {faqs._open_text()}.",'),
    ("app/main.py", 'f"- Order on WhatsApp: {WHATSAPP_ORDER_DISPLAY} (send \\"hi\\")",', '*([f"- Order on WhatsApp: {WHATSAPP_ORDER_DISPLAY} (send \\"hi\\")"] if WHATSAPP_ORDER_DISPLAY else []),'),
    ("app/main.py", 'f"- Prices: ₹{min(prices):g} to ₹{max(prices):g} per dish; most mains also come as half portions",', 'f"- Prices: ₹{min(prices):g} to ₹{max(prices):g} per dish",'),
    # WhatsApp templates
    ("app/whatsapp/templates.py", 'SITE = "https://tulsifoods.app"', 'SITE = business.site_url'),
    ("app/whatsapp/templates.py", '"body": ("Hi {{1}}, thank you for ordering from Tulsi Foods! 🙏\\n\\n"', '"body": (f"Hi {{{{1}}}}, thank you for ordering from {business.name}! 🙏\\n\\n"'),
    ("app/whatsapp/templates.py", '"example": ["142", "Drop: Asha, 12 Luz Church Road, Mylapore. Phone 98123 45678. Prepaid, collect nothing."],', '"example": ["142", "Drop: Asha, 5 Example Street. Phone 98123 45678. Prepaid, collect nothing."],'),
    ("app/whatsapp/templates.py", '"12 Luz Church Road, Mylapore (near the temple tank)",', '"5 Example Street (near the temple tank)",'),
    ("app/whatsapp/templates.py", '"header": "Tulsi kitchen alert",', '"header": "Kitchen alert",'),
    ("app/whatsapp/templates.py", 'drop Asha, 12 Luz Church Road, prepaid."', 'drop Asha, 5 Example Street, prepaid."'),
    ("app/whatsapp/flows/checkout.json", '"__example__": "12, Luz Church Road, Mylapore"', '"__example__": "5, Example Street"'),
    ("app/whatsapp/flows/checkout.json", '"description": "34 Murrays Gate Road, Alwarpet"', '"description": "Collect from the kitchen"'),
    # scripts and tests
    ("scripts/purge_orders.py", 'tulsi.db.bak-<timestamp>', 'kitchen.db.bak-<timestamp>'),
    (".env.example", 'WHATSAPP_VERIFY_TOKEN=tulsi_verify', 'WHATSAPP_VERIFY_TOKEN='),
    (".env.example", 'TULSI_ADMIN_TOKEN=tulsi', 'ADMIN_TOKEN='),
    (".env.example", '# Petpooja POS integration — from Malvi Vaghela once staging/prod is issued.', '# Petpooja POS integration (India). Optional; leave blank to run without a POS.'),
    # comments
    ("app/config.py", "Swiggy data shows a consistent 5%", "Aggregator data shows a consistent 5%"),
    ("app/config.py", "# Meta business portfolio (tulsi.foods_chennai) that owns the WhatsApp", "# Meta business portfolio that owns the WhatsApp"),
    ("app/config.py", "pre-filled with Tulsi's VPA and the", "pre-filled with your VPA and the"),
    ("app/config.py", '(e.g. "tulsifoods@oksbi")', '(e.g. "yourname@bank")'),
    ("app/config.py", "referrer to tulsifoods.app in Google Cloud Console", "referrer to your domain in Google Cloud Console"),
    ("app/db.py", "# ---- platform stats (Swiggy/Zomato manual entry, Google auto-refreshed) ----", "# ---- platform stats (manual entry, Google auto-refreshed) ----"),
    ("app/db.py", "real order history spans 11 years across Swiggy/Zomato/walk-in/phone, none", "real order history spans years across marketplaces/walk-in/phone, none"),
    ("app/delivery/config.py", "# Pickup location — Tulsi Foods, Alwarpet", "# Pickup location (the kitchen)"),
    ("app/delivery/porter.py", "with no merchant API and no Chennai", "with no merchant API and no city-specific"),
    ("app/petpooja/catalog.py", "menu.json prices are Swiggy platform averages", "menu.json prices are marketplace averages"),
    ("app/petpooja/mapping.py", "(the data/menu.json slug, sourced from Swiggy exports)", "(the data/menu.json slug)"),
    ("app/petpooja/mapping.py", "Every Tulsi Foods delivery goes through Borzo", "Every delivery goes through Borzo"),
    ("app/reviews.py", "Swiggy, Zomato,", "other platforms,"),
    ("app/qr.py", "The flyer QR encodes https://tulsifoods.app/f", "The flyer QR encodes <your site>/f"),
    ("app/wa_link.py", "The bot sends https://tulsifoods.app/o/<token>", "The bot sends <your site>/o/<token>"),
]

REGEX_RULES += [
    ("app/petpooja/config.py", r"(?s)Credentials are issued by the Petpooja team.*?PETPOOJA_INTEGRATION\.md\.\n",
     "Credentials are issued by Petpooja per restaurant and per environment.\n"
     "Everything here is blank/inert until they are set; setting the four\n"
     "credential vars is what turns the integration on (see `app/orders.py` and\n"
     "`app/webhooks.py`, both gated on PETPOOJA_APP_KEY).\n\n"
     "Production endpoints differ from the sandbox defaults below: override all\n"
     "three (save_order, update_order_status, rider_status_update) with the\n"
     "environment variables in .env.example.\n\n"
     "PETPOOJA_REST_ID must be the restaurant's *mapping code*, not the numeric\n"
     "outlet id. With the numeric id Save Order still reports success, but the\n"
     "order never reaches the POS terminal.\n"),
    ("app/telegram.py", r"\bTULSI_ADMIN_URL\b", "SITE_URL"),
]

# ---- admin: no aggregator-specific fields
REGEX_RULES += [
    ("app/templates/admin.html", r'\n\s*<option value="(swiggy|zomato)">[A-Za-z]+</option>', ""),
    ("app/templates/admin.html", r'(?s)\n        <div style="display:flex; gap:8px; align-items:center;">\n          <span style="width:64px; font-size:13px;">(Swiggy|Zomato)</span>.*?</div>', ""),
    ("app/templates/admin.html", r"Swiggy and Zomato don't have a review API — check their dashboard and update these by hand\. ", ""),
    ("app/templates/admin.html", r"No system has ever tallied 11 years of Swiggy \+ Zomato \+ walk-in \+ phone orders — this app's own order count is only the tiny slice placed through the website\. ",
     "The app only counts orders placed through the website. "),
    ("app/static/admin.js", r"(?s)\n      if \(s\.swiggy\) \{.*?\n      if \(s\.zomato\) \{.*?\n      \}", ""),
    ("app/static/admin.js", r"(?s)\n      const swiggyRating = .*?\n      toast\(\"Numbers saved", '\n      toast("Numbers saved'),
    ("app/static/admin.js", r' swiggy: "Swiggy", zomato: "Zomato",', ""),
    ("app/static/admin.js", r"Tulsi Admin", "Admin"),
    ("app/templates/*.html", r"swiggy_rating\(", "external_rating("),
]

# ---- templates: brand, site url, storage keys
_T = "app/templates/*.html"
REGEX_RULES += [
    (_T, r'\(group ~ " at Tulsi Foods"\)', '(group ~ " at " ~ biz.name)'),
    (_T, r'\("https://tulsifoods\.app/menu/" ~ item\.id\)', '(site_url ~ "/menu/" ~ item.id)'),
    (_T, r"https://tulsifoods\.app", "{{ site_url }}"),
    (_T, r"tulsifoods\.app", "{{ site_url }}"),
    (_T, r"Tulsi Foods,? (Mylapore|Alwarpet)(,? (Chennai|&amp; Mylapore))?", "{{ biz.name }}"),
    (_T, r"Tulsi Foods", "{{ biz.name }}"),
    (_T, r"Tulsi's VPA", "The shop's VPA"),
    (_T, r"Tulsi Kitchen", "Kitchen"),
    (_T, r"tulsi_", "cp_"),
    (_T, r"Kavita has started", "The kitchen has started"),
    (_T, r" so Chennai results come first", " so local results come first"),
    (_T, r'\s*<div class="f-aka">.*?</div>|\s*<p class="f-aka">.*?</p>', ""),
    (_T, r'\n\s*<a href="https?://(maps\.app\.goo\.gl|www\.swiggy\.com|zoma\.to|jsdl\.in|www\.postcard\.inc)[^"]*"[^>]*>[^<]*</a>', ""),
    (_T, r'\n\s*<script async src="https://www\.googletagmanager\.com/gtag/js\?id=G-[A-Z0-9]+"></script>', ""),
    (_T, r"gtag\('config', 'G-[A-Z0-9]+'\);", ""),
    ("app/static/kitchen.js", r"Tulsi Kitchen", "Kitchen"),
    ("app/static/kitchen.js", r' \+ ", Chennai"\)', ')'),
    ("app/static/kitchen.js", r'k\.address \|\| "34 Murrays Gate Road, Alwarpet"', 'k.address || ""'),
    ("app/static/sw.js", r"tulsi-shell", "shell"),
    ("tests/smoke.py", r"TULSI_TEST_PORT", "TEST_PORT"),
]

RULES.append(("app/main.py", 'templates.env.globals["biz"] = biz', 'templates.env.globals["biz"] = biz\ntemplates.env.globals["site_url"] = biz.site_url'))

_AT = "app/templates/"
RULES += [
    (_AT + "base.html", "Tulsi Foods — pure vegetarian, home-style North Indian food in Mylapore, Chennai. Order online for delivery or pickup, no platform fees.",
     "{{ biz.name }} — {{ biz.tagline }}. Order online for delivery or pickup, no platform fees."),
    (_AT + "base.html", "<title>Tulsi Foods — Pure Veg North Indian Food, Mylapore, Chennai</title>", "<title>{{ biz.name }}</title>"),
    (_AT + "category.html", " at Tulsi Foods, {{ count }} item{{ '' if count == 1 else 's' }} from ₹{{ price_low | int }}. Pure veg, home-style North Indian food delivered in Mylapore, Alwarpet &amp; Teynampet, Chennai.",
     " at {{ biz.name }}, {{ count }} item{{ '' if count == 1 else 's' }} from ₹{{ price_low | int }}."),
    (_AT + "category.html", "Everything in this category at Tulsi Foods: pure vegetarian, home-style North Indian food cooked to order in Mylapore, Chennai. Prices are today's prices; delivery is confirmed on WhatsApp.",
     "Everything in this category at \" ~ biz.name ~ \". Prices are today's prices; delivery is confirmed on WhatsApp."),
    (_AT + "category.html", "near Mylapore? Everything below is cooked to order in our Alwarpet kitchen and delivered across South Chennai.",
     "near {{ biz.locality }}? Everything below is cooked to order in our {{ biz.locality }} kitchen."),
    (_AT + "category.html", "{% set sw = swiggy_rating(item.id) %}{% if sw %}<div class=\"item-rating\">★ {{ sw.rating }} · {{ sw.count_text }} on Swiggy</div>{% endif %}",
     "{% set sw = external_rating(item.id) %}{% if sw %}<div class=\"item-rating\">★ {{ sw.rating }} · {{ sw.count_text }}</div>{% endif %}"),
    (_AT + "delivery.html", "Where Tulsi Foods delivers in Chennai (Mylapore, Alwarpet, Teynampet, Adyar, T. Nagar and nearby) and what delivery costs. Pure vegetarian North Indian food, cooked to order.",
     "Where {{ biz.name }} delivers and what delivery costs."),
    (_AT + "delivery.html", "We deliver from the kitchen on Murrays Gate Road, Alwarpet. A Porter rider is booked for each order,",
     "We deliver from the kitchen at {{ biz.street_address }}. A rider is booked for each order,"),
    (_AT + "item.html", " pure veg, cooked fresh near you in Mylapore, Alwarpet &amp; Teynampet, Chennai. Order online, no platform fees.", " Order online, no platform fees."),
    (_AT + "item.html", " Price ₹{{ item.price }} · Order Online in Chennai | Tulsi Foods</title>", " Price ₹{{ item.price }} · Order Online | {{ biz.name }}</title>"),
    (_AT + "item.html", "{{ sw.count_text }} ratings on <a href=\"{{ sw.url }}\" target=\"_blank\" rel=\"nofollow noopener\">Swiggy</a>", "{{ sw.count_text }} ratings"),
    (_AT + "item.html", "{% set sw = swiggy_rating(item.id) %}", "{% set sw = external_rating(item.id) %}"),
    (_AT + "item.html", "Made fresh to order at Tulsi Foods, a home-style pure vegetarian kitchen in Mylapore, Chennai.", "Made fresh to order at {{ biz.name }}."),
    (_AT + "item.html", "<h2>{{ item.name }} near you in Chennai</h2>", "<h2>{{ item.name }} near you</h2>"),
    (_AT + "item.html", "Our kitchen is on Murrays Gate Road, Alwarpet, and delivers it hot to", "Our kitchen is at {{ biz.street_address }} and delivers it hot to"),
    (_AT + "menu.html", "Full menu, prices and daily availability for Tulsi Foods: pure vegetarian North Indian thalis, parathas, chaats, sabzi and more in Mylapore, Chennai. Order online for delivery or pickup.",
     "Full menu, prices and daily availability for {{ biz.name }}. Order online for delivery or pickup."),
    (_AT + "menu.html", "<title>Tulsi Foods Menu &amp; Prices · Tulsi Restaurant, Alwarpet &amp; Mylapore, Chennai</title>", "<title>{{ biz.name }} Menu &amp; Prices</title>"),
]

RULES += [
    ("Dockerfile", "COPY data/petpooja_menu_raw.json /app/petpooja_menu_raw.json.bundled\n", ""),
]
