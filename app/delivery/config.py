"""Delivery partner configuration — Borzo (primary) + Shiprocket (fallback)."""
import os

# Borzo API auth (static token from Borzo dashboard → Integration)
BORZO_AUTH_TOKEN = os.environ.get("BORZO_AUTH_TOKEN", "")
BORZO_BASE_URL = os.environ.get(
    "BORZO_BASE_URL",
    "https://robotapitest-in.borzodelivery.com/api/business/1.8",  # test env
)
BORZO_CALLBACK_TOKEN = os.environ.get("BORZO_CALLBACK_TOKEN", "")  # for webhook verification

# Shiprocket API auth (fallback — email + password for /auth/login)
SHIPROCKET_API_EMAIL = os.environ.get("SHIPROCKET_API_EMAIL", "")
SHIPROCKET_API_PASSWORD = os.environ.get("SHIPROCKET_API_PASSWORD", "")
SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"

# Pickup location — Tulsi Foods, Alwarpet
PICKUP_ADDRESS = "34, Murrays Gate Road, Alwarpet, Chennai, 600018, Tamil Nadu, India"
PICKUP_PINCODE = "600018"
PICKUP_LAT = 13.038909  # resolved from the Google Maps listing itself
PICKUP_LNG = 80.256394
PICKUP_PHONE = "9940062840"  # restaurant contact for rider

# Default food parcel weight (kg) — used for serviceability & rate lookups
DEFAULT_WEIGHT_KG = 1.5

# Delivery fee safety: if quote exceeds this, flag for admin review
MAX_DELIVERY_FEE = 200

# Shiprocket channel ID for order-based tracking (fallback only).
# Find in Shiprocket Panel → Sales Channels.
SHIPROCKET_CHANNEL_ID = int(os.getenv("SHIPROCKET_CHANNEL_ID", "11901391"))
