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

# GST for direct (non-aggregator) orders. Swiggy data shows a consistent 5%
# charged on every order (the standard non-ITC restaurant rate) — aggregators
# remit that themselves under Section 9(5), which doesn't cover direct sales,
# so this app has to collect it itself. Confirm the rate/registration status
# with your CA before changing — this mirrors observed data, not tax advice.
GST_RATE = 0.05
GST_ENABLED = True

# Packing charge for direct orders — flat, with a step up for large orders.
# Mirrors the existing "Container Charge" already used elsewhere in the
# business; retune these two numbers freely, they're a starting estimate.
PACKING_FEE = 20
PACKING_FEE_LARGE_ORDER_THRESHOLD = 1000
PACKING_FEE_LARGE_ORDER = 40

# GSTIN — shown on order confirmations/receipts once set. Blank until filled in.
GSTIN = os.environ.get("GSTIN", "")

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

# Master switch for outbound WhatsApp. Set to "1" once Meta business verification
# completes and the number is registered; until then, status notifications are
# routed to the SMS fallback (Twilio). Flip this (no code change) to go live.
WHATSAPP_ACTIVE = os.environ.get("WHATSAPP_ACTIVE", "") == "1"

# Twilio SMS fallback (used when WhatsApp templates/number aren't verified yet).
# Auth via API Key SID + secret, scoped to an Account SID (SDK pattern).
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_ID", "")   # AC...
TWILIO_API_KEY = os.environ.get("TWILIO_SID", "")              # SK...
TWILIO_API_SECRET = os.environ.get("TWILIO_CLIENT_SECRET", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")                # E.164 sender / sender ID
# Trial accounts (verified recipients + pre-defined templates only) block custom
# bodies with error 572006 and only deliver to verified numbers — so on trial the
# client SKIPS (can't send meaningful order SMS). Set to "1" while on the free
# trial; flip to "" after upgrading to a paid account with an Indian DLT sender
# ID for real free-form order-status SMS.
TWILIO_TRIAL = os.environ.get("TWILIO_TRIAL", "1") == "1"
TWILIO_API_URL = "https://api.twilio.com"

# Telegram admin-alert on new orders (no Meta, no sender-ID). Sends mom a message
# when an order lands so she knows without opening admin. TELEGRAM_BOT_TOKEN from
# @BotFather; TELEGRAM_CHAT_ID is her bot-chat id (talk to @userinfobot to get it).
# Empty token = disabled; the admin page beep remains the fallback.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Static UPI payment collection (no gateway needed). When a customer pays by UPI,
# we hand them a upi:// deep link (and QR) pre-filled with Tulsi's VPA and the
# order amount; the credit is confirmed manually by the kitchen. UPI_VPA is the
# only required setting (e.g. "tulsifoods@oksbi"); UPI_PAYEE_NAME shows on the
# pay screen. Empty VPA = UPI hidden at checkout (COD only).
UPI_VPA = os.environ.get("UPI_VPA", "")
UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", "Tulsi Foods")
UPI_TXN_NOTE = os.environ.get("UPI_TXN_NOTE", "Tulsi Foods order payment")


def upi_uri(amount: float | int, txn_ref: str, payee_name: str | None = None) -> str:
    """Build a UPI Intent deep-link the customer's UPI app can open.

    Uses the standard UPI Intent spec (pa/pn/am/cu/tn/tr). The transaction
    reference doubles as the order id so a UPI payment notice can be matched.
    """
    from urllib.parse import quote
    pn = payee_name or UPI_PAYEE_NAME
    tr = quote(txn_ref)
    tn = quote(UPI_TXN_NOTE)
    return (
        f"upi://pay?pa={UPI_VPA}&pn={quote(pn)}&am={amount}&cu=INR"
        f"&tn={tn}&tr={tr}"
    )

# Shiprocket Quick (hyperlocal delivery) — credentials for API auth
SHIPROCKET_API_EMAIL = os.environ.get("SHIPROCKET_API_EMAIL", "")
SHIPROCKET_API_PASSWORD = os.environ.get("SHIPROCKET_API_PASSWORD", "")

# Mom's WhatsApp phone number — messages from this number trigger admin commands
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")

# Public base URL for admin links (used in Telegram kitchen alerts).
TULSI_ADMIN_URL = os.environ.get("TULSI_ADMIN_URL", "https://tulsifoods.app")

# Google Business Profile "ask for review" short link
GOOGLE_REVIEW_LINK = "https://g.page/r/CbCaykOYyQTPEAE/review"

# Google Places API (New) — server-side key, optional; live rating/review
# count on /about. Cached server-side (see app/reviews.py) so this stays
# well inside the 5,000 free Place Details Pro calls/month. Unset = feature
# just stays hidden. (Not the same key as GOOGLE_MAPS_JS_API_KEY below —
# this one should be IP-restricted, not exposed to browsers.)
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
GOOGLE_PLACE_ID = os.environ.get("GOOGLE_PLACE_ID", "")

# Google Maps JavaScript API — client-side key, optional; powers the address
# autocomplete + map pin in checkout. This key IS meant to be visible in
# page source (that's how Maps JS API keys work) — restrict it by HTTP
# referrer to tulsifoods.app in Google Cloud Console, not by keeping it
# secret. Unset = checkout falls back to a plain address textarea.
GOOGLE_MAPS_JS_API_KEY = os.environ.get("GOOGLE_MAP_API_KEY", "")
