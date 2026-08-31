"""Pure conversions between our order/menu shapes and Petpooja's payloads.

Field names and nesting here match the worked example on the "Save Order"
endpoint page at https://onlineorderingapisv210.docs.apiary.io (click into
the 200 response — the flat field list on that page is summary prose and
disagrees slightly on nesting; the JSON example is what's authoritative).

KNOWN GAP, not yet resolved: `OrderItem.id` below is our own menu item_id
(from data/menu.json, sourced from Swiggy exports), not Petpooja's item id.
Petpooja's POS almost certainly expects *its own* catalog item ids in Save
Order. We won't know those until we do a Fetch Menu call and reconcile it
against data/menu.json — a real follow-up task, not a config toggle. Until
that reconciliation happens, Save Order calls may be accepted but attribute
items incorrectly (or get rejected) on Petpooja's side. Verify against a
real sandbox order the moment credentials arrive.

Also approximate, flagged inline: per-item/per-charge GST breakdown. Our
order model keeps a single `gst_amount` on the order (see app/orders.py
gst_for()); Petpooja wants tax itemised per line and per charge
(service/delivery/packing). We prorate the order-level GST across items by
price share and split each into CGST/SGST halves, which is standard for
intra-state GST but is a derived approximation, not sourced from a real
per-item tax table. Confirm this reconciles with Petpooja's own tax setup
for the restaurant before relying on it for filing.
"""
from datetime import datetime

from .config import (
    PETPOOJA_REST_ID,
    PETPOOJA_RES_ADDRESS,
    PETPOOJA_RES_CONTACT,
    PETPOOJA_RES_NAME,
)

# Petpooja Order Callback status codes -> our internal order status.
# [-1 = Cancelled, 1/2/3 = Accepted, 4 = Dispatch, 5 = Food Ready, 10 = Delivered]
CALLBACK_STATUS_MAP = {
    "-1": "cancelled",
    "1": "preparing",
    "2": "preparing",
    "3": "preparing",
    "4": "out_for_delivery",
    "5": "ready",
    "10": "delivered",
}

# order_type letter code inferred from the Save Order example ("H" for a
# home-delivery sample order) — not spelled out anywhere in the docs
# reference prose. Verify against a real call; Petpooja support can confirm
# the full code list (dine-in is presumably "D").
_ORDER_TYPE_CODE = {"delivery": "H", "pickup": "P"}

# payment_type inferred similarly from the "COD" example value.
_PAYMENT_TYPE_CODE = {"cod": "COD", "upi": "ONLINE"}


def _split_cgst_sgst(amount: float, rate_pct: float, tax_id_base: str) -> list[dict]:
    half = round(amount / 2, 2)
    return [
        {"id": f"{tax_id_base}-c", "name": "CGST", "tax_percentage": str(rate_pct / 2), "amount": str(half)},
        {"id": f"{tax_id_base}-s", "name": "SGST", "tax_percentage": str(rate_pct / 2), "amount": str(half)},
    ]


def order_to_save_order_payload(order: dict, callback_url: str, gst_rate: float) -> dict:
    """Build the `orderinfo` body for POST save_order from our `db.get_order()` row.

    `order` is the dict returned by app.db.get_order() (has `items`, totals,
    customer_name/phone, delivery_* fields). `gst_rate` is app.config.GST_RATE
    (e.g. 0.05), used only to label the prorated per-item tax percentage.
    """
    subtotal = float(order["subtotal"])
    packing_fee = float(order.get("packing_fee") or 0)
    delivery_fee = float(order.get("delivery_fee") or 0)
    gst_amount = float(order.get("gst_amount") or 0)
    total = float(order["total"])
    order_type = order.get("order_type", "delivery")
    payment_method = (order.get("payment_method") or "cod").lower()

    # Prorate order-level GST across items by price share (see module docstring).
    taxable_base = subtotal + packing_fee
    item_lines = []
    for it in order["items"]:
        line_total = float(it["price"]) * float(it["qty"])
        share = (line_total / taxable_base) if taxable_base else 0
        item_gst = round(gst_amount * share, 2)
        item_lines.append({
            "id": str(it["item_id"]),  # Petpooja catalog id TBD — see docstring
            "name": it["name"],
            "tax_inclusive": False,
            "gst_liability": "restaurant",
            "item_tax": _split_cgst_sgst(item_gst, gst_rate * 100, str(it["item_id"])),
            "item_discount": "0",
            "price": f"{float(it['price']):.2f}",
            "final_price": f"{line_total:.2f}",
            "quantity": str(it["qty"]),
            "description": "",
            "variation_name": "",
            "variation_id": "",
            "AddonItem": {"details": []},
        })

    order_details = {
        "orderID": str(order["id"]),
        "preorder_date": "",
        "preorder_time": "",
        "service_charge": "0",
        "sc_tax_amount": "0",
        "delivery_charges": f"{delivery_fee:.2f}",
        "dc_tax_percentage": "0",
        "dc_tax_amount": "0",
        "packing_charges": f"{packing_fee:.2f}",
        "pc_tax_percentage": "0",
        "pc_tax_amount": "0",
        "order_type": _ORDER_TYPE_CODE.get(order_type, "H"),
        "advanced_order": "N",
        "urgent_order": False,
        "payment_type": _PAYMENT_TYPE_CODE.get(payment_method, "COD"),
        "table_no": "",
        "no_of_persons": "0",
        "discount_total": "0",
        "discount_type": "F",
        "tax_total": f"{gst_amount:.2f}",
        "total": f"{total:.2f}",
        "description": order.get("instructions") or "",
        "created_on": order.get("created_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "enable_delivery": 1 if order_type == "delivery" else 0,
        "min_prep_time": 20,
        "callback_url": callback_url,
        "collect_cash": f"{total:.2f}" if payment_method == "cod" else "0",
    }

    customer_details = {
        "email": "",
        "name": order.get("customer_name") or "Customer",
        "address": order.get("delivery_address") or "",
        "phone": order.get("customer_phone") or "",
        "latitude": order.get("delivery_lat") or "",
        "longitude": order.get("delivery_lng") or "",
    }

    return {
        "OrderInfo": {
            "Restaurant": {
                "details": {
                    "res_name": PETPOOJA_RES_NAME,
                    "address": PETPOOJA_RES_ADDRESS,
                    "contact_information": PETPOOJA_RES_CONTACT,
                    "restID": PETPOOJA_REST_ID,
                }
            },
            "Customer": {"details": customer_details},
            "Order": {"details": order_details},
            "OrderItem": {"details": item_lines},
            "Tax": {"details": []},
            "Discount": {"details": []},
        }
    }


def petpooja_status_to_order_status(status_code: str) -> str | None:
    """Map an Order Callback `status` code to our ORDER_STATUSES value."""
    return CALLBACK_STATUS_MAP.get(str(status_code))
