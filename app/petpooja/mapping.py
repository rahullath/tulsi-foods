"""Pure conversions between our order/menu shapes and Petpooja's payloads.

Field names and nesting here follow the Sep 2026 "API Guide for Placing
Orders on Petpooja POS" (temp/API Guide for Placing Orders on Petpooja
POS.pdf), Petpooja's newer worked example, which disagrees in a couple of
spots with the older Apiary docs at https://onlineorderingapisv210.docs.apiary.io
— notably order-level `Tax.details` (required, was previously sent empty)
and `addon_items` as a flat list (Apiary nests it as `AddonItem.details`).
Went with the newer guide since it's what Petpooja pointed at for the
current sandbox review; flip back to the Apiary shape if the sandbox
rejects it.

RESOLVED (Sep 2026, §3.2 reconciliation landed): OrderItem.id used to be our
own menu item_id (the data/menu.json slug, sourced from Swiggy exports)
instead of Petpooja's real catalog id — Save Order was accepted (success=1)
but items didn't exist in the POS catalogue, so orders were invisible on the
dashboard. Now app/petpooja/catalog.py resolves every slug to the catalogue's
real `itemid` (the id Petpooja itself pushes in Menu Trigger, cached in
data/petpooja_menu_raw.json), keyed by item name, and falls back to the slug
with a warning if unmapped. Half portions share the base item's id.

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


def _order_level_tax_details(gst_amount: float, rate_pct: float) -> list[dict]:
    """Order-level `Tax.details` — a separate, required breakdown from the
    per-item `item_tax` above (see the "Tax & Discounts" section of the Sep
    2026 Save Order API guide in temp/). restaurant_liable_amt mirrors the
    tax amount since gst_liability is "restaurant" for every item here."""
    half_amt = round(gst_amount / 2, 2)
    half_rate = round(rate_pct / 2, 2)
    return [
        {"id": "1", "title": "CGST", "type": "P", "price": f"{half_rate}%",
         "tax": f"{half_amt:.2f}", "restaurant_liable_amt": f"{half_amt:.2f}"},
        {"id": "2", "title": "SGST", "type": "P", "price": f"{half_rate}%",
         "tax": f"{half_amt:.2f}", "restaurant_liable_amt": f"{half_amt:.2f}"},
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
    from .catalog import map_order_items
    mapped_items = map_order_items(order["items"])
    item_lines = []
    for it in mapped_items:
        unit_price = float(it["price"])
        line_total = unit_price * float(it["qty"])
        share = (line_total / taxable_base) if taxable_base else 0
        item_gst = round(gst_amount * share, 2)
        # price/final_price are per single unit, even at qty > 1 — the
        # doc's worked example is explicit that quantity is NOT multiplied
        # in here (the qty-scaled total is carried separately in the
        # order-level `total` key). final_price = price - item_discount.
        item_discount = float(it.get("item_discount") or 0)
        final_price = unit_price - item_discount
        item_lines.append({
            "id": it["petpooja_item_id"],  # real catalogue id (see app/petpooja/catalog.py)
            "name": it["name"],
            # Mirror the catalogue's own tax treatment per item (Petpooja
            # pushes `tax_inclusive: true` on these POS items): telling the
            # POS "inclusive" stops it materializing GST again on top of the
            # exact total we already collected from the customer. The item
            # 'price' sent here stays as our checkout price and the tax
            # lines below still reflect the GST line our customer actually
            # paid — matching Petpooja's flag without changing the money.
            "tax_inclusive": it.get("petpooja_tax_inclusive", False),
            "gst_liability": "restaurant",
            "item_tax": _split_cgst_sgst(item_gst, gst_rate * 100, str(it["item_id"])),
            "tax_percentage": f"{gst_rate * 100:.2f}",
            "item_discount": str(it.get("item_discount", "0")),
            "price": f"{unit_price:.2f}",
            "final_price": f"{final_price:.2f}",
            "quantity": str(it["qty"]),
            "description": "",
            "variation_name": it.get("variation_name", ""),
            "variation_id": str(it.get("variation_id", "")),
            # Sent under BOTH keys: the flat "addon_items" key alone (new
            # guide) was confirmed silently dropped on a real sandbox order
            # (Sep 2026) — item saved fine but the addon never appeared on
            # the receipt. Sending it nested under "AddonItem.details" too
            # (the older Apiary shape) fixed it — receipt then showed the
            # addon and the correct addon-inclusive total. Never isolated
            # which key Petpooja's backend actually reads since both were
            # sent together; harmless to keep sending both indefinitely.
            "addon_items": it.get("addon_items", []),
            "AddonItem": {"details": it.get("addon_items", [])},
        })

    created_on = order.get("created_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    # advanced_order is always "N" (we don't support scheduled-ahead orders)
    # — the doc is explicit that preorder_date/time must then mirror
    # created_on, not be left blank.
    preorder_date, _, preorder_time = created_on.partition(" ")

    # Packing charge IS folded into our taxable base (see gst_for()'s
    # docstring), so its share of gst_amount is real, not zero. Prorate the
    # same way item_gst is prorated above — required field per the API
    # guide, previously hardcoded to "0" (docs/PETPOOJA_INTEGRATION.md §3.4).
    pc_tax_amount = round(gst_amount * (packing_fee / taxable_base), 2) if taxable_base else 0.0
    order_discount = float(order.get("discount_total") or 0)
    # Per the API guide: "Total = Item Final Price [- Order level Discount]
    # + GST [if liable by restaurant] + Packing Charges. The 'Total' should
    # only include the amount due to the restaurant" — delivery_charges is
    # explicitly excluded since that money belongs to Borzo, not us. This is
    # NOT the same number as our own order["total"] (which is the
    # customer-facing grand total, used below for collect_cash).
    restaurant_total = subtotal - order_discount + gst_amount + packing_fee

    order_details = {
        "orderID": str(order["id"]),
        "preorder_date": preorder_date,
        "preorder_time": preorder_time,
        "service_charge": "0",
        "sc_tax_amount": "0",
        "delivery_charges": f"{delivery_fee:.2f}",
        # Genuinely 0, not an oversight: gst_for() explicitly keeps delivery
        # fee outside the taxable base (it's a Borzo pass-through, not a
        # restaurant charge) — unlike pc_tax_percentage below, which isn't.
        "dc_tax_percentage": "0",
        "dc_tax_amount": "0",
        "packing_charges": f"{packing_fee:.2f}",
        "pc_tax_percentage": f"{gst_rate * 100:.2f}",
        "pc_tax_amount": f"{pc_tax_amount:.2f}",
        "order_type": _ORDER_TYPE_CODE.get(order_type, "H"),
        "advanced_order": "N",
        "urgent_order": False,
        "payment_type": _PAYMENT_TYPE_CODE.get(payment_method, "COD"),
        "table_no": "",
        "no_of_persons": "0",
        "discount_total": str(order.get("discount_total", "0")),
        "discount_type": order.get("discount_type", "F"),
        "tax_total": f"{gst_amount:.2f}",
        "total": f"{restaurant_total:.2f}",
        "description": order.get("instructions") or "",
        "created_on": created_on,
        # 0 = third-party rider, 1 = restaurant's own rider — NOT "is this a
        # delivery order". Every Tulsi Foods delivery goes through Borzo (a
        # third-party courier, see app/delivery/), never restaurant staff,
        # so this must always be 0. Confirmed the hard way: with the old
        # `1 if order_type == "delivery" else 0` logic, every sandbox test
        # order's receipt showed "Home Delivery (Self delivery)" — wrong.
        "enable_delivery": 0,
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

    # Docs' Save Order example carries the order-level discount here as well as
    # in Order.details.discount_total. Previously always sent `[]` even when
    # discounted. `id` is a placeholder (same catalog-id reconciliation gap as
    # item ids, see module docstring); price mirrors discount_total.
    discount_lines = []
    if order_discount > 0:
        discount_lines.append({
            "id": "0",
            "title": "Discount",
            "type": order.get("discount_type", "F"),
            "price": str(order.get("discount_total", order_discount)),
        })

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
            "Tax": {"details": _order_level_tax_details(gst_amount, gst_rate * 100)},
            "Discount": {"details": discount_lines},
        }
    }


def petpooja_status_to_order_status(status_code: str) -> str | None:
    """Map an Order Callback `status` code to our ORDER_STATUSES value."""
    return CALLBACK_STATUS_MAP.get(str(status_code))
