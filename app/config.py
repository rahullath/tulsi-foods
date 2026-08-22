import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = lambda *a, **k: None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
MENU_FILE = DATA_DIR / "menu.json"
DB_FILE = DATA_DIR / "tulsi.db"

ADMIN_TOKEN = os.environ.get("TULSI_ADMIN_TOKEN", "tulsi")

# Delivery config (from spec §7, real distance data)
DELIVERY_ZONES = [
    {"name": "A (core)", "max_km": 3.0, "fee": 30, "min_order": 250},
    {"name": "B", "max_km": 5.0, "fee": 50, "min_order": 300},
    {"name": "C", "max_km": 7.0, "fee": 70, "min_order": 350},
]

FREE_DELIVERY_ABOVE = 700  # optional: free delivery over this amount

ORDER_STATUSES = [
    "new",
    "preparing",
    "ready",
    "out_for_delivery",
    "delivered",
    "cancelled",
]

# WhatsApp Cloud API (optional — bot runs in dry-run/log mode without these)
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "tulsi_verify")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
WHATSAPP_GRAPH_VERSION = "v26.0"
WHATSAPP_GRAPH_URL = "https://graph.facebook.com"

# If set, the bot appends replies here instead of sending to WhatsApp (dev mode)
WHATSAPP_DRY_LOG = os.environ.get("WHATSAPP_DRY_LOG", "data/whatsapp.log")

# Shiprocket Quick (hyperlocal delivery) — credentials for API auth
SHIPROCKET_API_EMAIL = os.environ.get("SHIPROCKET_API_EMAIL", "")
SHIPROCKET_API_PASSWORD = os.environ.get("SHIPROCKET_API_PASSWORD", "")

# Mom's WhatsApp phone number — messages from this number trigger admin commands
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")

# Google Business Profile "ask for review" short link
GOOGLE_REVIEW_LINK = "https://g.page/r/CbCaykOYyQTPEAE/review"
