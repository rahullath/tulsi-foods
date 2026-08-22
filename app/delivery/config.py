"""Delivery partner configuration — Shiprocket Quick (hyperlocal)."""
import os

# Shiprocket API auth (email + password for /auth/login)
SHIPROCKET_API_EMAIL = os.environ.get("SHIPROCKET_API_EMAIL", "")
SHIPROCKET_API_PASSWORD = os.environ.get("SHIPROCKET_API_PASSWORD", "")
SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"

# Pickup location — Tulsi Foods, Alwarpet
PICKUP_ADDRESS = "34, Murrays Gate Road, Alwarpet, Chennai, 600018, Tamil Nadu, India"
PICKUP_PINCODE = "600018"
PICKUP_LAT = 13.0340   # approximate — update if needed
PICKUP_LNG = 80.2574
PICKUP_PHONE = "9940062840"  # restaurant contact for rider

# Default food parcel weight (kg) — used for serviceability & rate lookups
DEFAULT_WEIGHT_KG = 1.5

# Delivery fee safety: if Shiprocket quote exceeds this, flag for admin review
MAX_DELIVERY_FEE = 200

# Shiprocket channel ID for order-based tracking.
# Find in Shiprocket Panel → Sales Channels.
SHIPROCKET_CHANNEL_ID = int(os.getenv("SHIPROCKET_CHANNEL_ID", "11901391"))
