"""Petpooja Integration Platform API config — PetpoojaOnlineOrdering V2.1.0.

Credentials are issued by the Petpooja team per restaurant (restID) and per
environment (staging/production) — see the vendor thread with Malvi Vaghela.
Everything here is blank/inert until those arrive; setting the four
credential vars is what flips the integration on (see `app/orders.py` and
`app/webhooks.py`, both gated on PETPOOJA_APP_KEY).

Endpoint URLs below are the "Dev URL"s documented at
https://onlineorderingapisv210.docs.apiary.io — Petpooja's production URLs
may differ and should be confirmed when credentials are handed over; override
via env if so.
"""
import os

PETPOOJA_APP_KEY = os.environ.get("PETPOOJA_APP_KEY", "")
PETPOOJA_APP_SECRET = os.environ.get("PETPOOJA_APP_SECRET", "")
PETPOOJA_ACCESS_TOKEN = os.environ.get("PETPOOJA_ACCESS_TOKEN", "")
PETPOOJA_REST_ID = os.environ.get("PETPOOJA_REST_ID", "")

# Outbound (we call Petpooja). Fetch Menu / Update Order Status / Rider webhook
# share one API Gateway host in the docs; Save Order uses a different one —
# that's documented, not a typo.
PETPOOJA_FETCH_MENU_URL = os.environ.get(
    "PETPOOJA_FETCH_MENU_URL",
    "https://qle1yy2ydc.execute-api.ap-southeast-1.amazonaws.com/V1/mapped_restaurant_menus",
)
PETPOOJA_SAVE_ORDER_URL = os.environ.get(
    "PETPOOJA_SAVE_ORDER_URL",
    "https://47pfzh5sf2.execute-api.ap-southeast-1.amazonaws.com/V1/save_order",
)
PETPOOJA_UPDATE_ORDER_STATUS_URL = os.environ.get(
    "PETPOOJA_UPDATE_ORDER_STATUS_URL",
    "https://qle1yy2ydc.execute-api.ap-southeast-1.amazonaws.com/V1/update_order_status",
)
PETPOOJA_RIDER_STATUS_URL = os.environ.get(
    "PETPOOJA_RIDER_STATUS_URL",
    "https://qle1yy2ydc.execute-api.ap-southeast-1.amazonaws.com/V1/rider_status_update",
)

# Inbound (Petpooja calls us): Push Menu, Order Callback, stock toggle, and
# store status aren't signed in the documented request shape, so we hand
# Petpooja URLs with this token baked in as a query param (?t=...) instead of
# trusting the payload alone. Generate a random value once credentials are
# being set up — see docs/HANDOFF.md.
PETPOOJA_WEBHOOK_TOKEN = os.environ.get("PETPOOJA_WEBHOOK_TOKEN", "")

# Static restaurant info Save Order wants in the top-level request (not the
# OrderInfo/Restaurant object) — reuse what Borzo already has on file.
from ..delivery.config import PICKUP_ADDRESS, PICKUP_PHONE  # noqa: E402

PETPOOJA_RES_NAME = "Tulsi Foods"
PETPOOJA_RES_ADDRESS = PICKUP_ADDRESS
PETPOOJA_RES_CONTACT = PICKUP_PHONE
