#!/usr/bin/env python3
"""Push the 5 sandbox test-scenario orders Petpooja asked for (Shivam
Tiwari's email, Sep 2026): Items+Tax, Item+Addon+Tax, Item+Variation+Tax,
Item+Discount+Tax, Item+Addon+Variation+Tax. Prints each resulting
petpooja_order_id to hand back to Petpooja for review.

Item/addon/variation names below are real entries from data/petpooja_items.csv
and data/petpooja_addons.csv (French Fries + "Add Ons(optional)" group,
Soft Drinks + "Full" size variation) — item/addon/variation IDs are
synthetic placeholders, same as Petpooja's own worked example in the API
guide, since we haven't reconciled against a real Fetch Menu response yet
(see the KNOWN GAP note in app/petpooja/mapping.py).

Requires PETPOOJA_APP_KEY / PETPOOJA_APP_SECRET / PETPOOJA_ACCESS_TOKEN /
PETPOOJA_REST_ID set in .env (see app/petpooja/config.py). Run from repo root:
    python3 -m scripts.petpooja_test_orders
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import GST_RATE, TULSI_ADMIN_URL  # noqa: E402
from app.petpooja.client import PetpoojaError, is_configured, save_order  # noqa: E402
from app.petpooja.config import PETPOOJA_WEBHOOK_TOKEN  # noqa: E402

CALLBACK_URL = f"{TULSI_ADMIN_URL}/webhook/petpooja/order-callback?t={PETPOOJA_WEBHOOK_TOKEN}"


def _order(order_id: str, items: list[dict], discount_total: str = "0", discount_type: str = "F") -> dict:
    subtotal = sum(float(it["price"]) * float(it["qty"]) for it in items)
    packing_fee = 0.0
    gst_amount = round((subtotal + packing_fee) * GST_RATE, 2)
    discount = float(discount_total) if discount_type == "F" else round(subtotal * float(discount_total) / 100, 2)
    total = subtotal + packing_fee + gst_amount - discount
    return {
        "id": order_id,
        "items": items,
        "subtotal": subtotal,
        "packing_fee": packing_fee,
        "delivery_fee": 0.0,
        "gst_amount": gst_amount,
        "total": total,
        "discount_total": discount_total,
        "discount_type": discount_type,
        "order_type": "delivery",
        "payment_method": "cod",
        "customer_name": "Petpooja Sandbox Test",
        "customer_phone": "9876543210",
        "delivery_address": "123, Test Street, Chennai",
        "delivery_lat": "13.0827",
        "delivery_lng": "80.2707",
        "instructions": "",
        "created_at": None,
    }


# clientOrderID must be unique per run — confirmed the hard way: re-saving
# under an already-seen PPTEST-N id came back "success" but silently no-op'd
# (unit price and order status stayed exactly as the first save left them).
_RUN = time.strftime("%m%d-%H%M%S")

SCENARIOS = {
    "1_items_and_tax": _order(
        f"PPTEST-{_RUN}-1",
        [{"item_id": "1001", "name": "Vanilla Ice Cream", "price": 120.0, "qty": 2}],
    ),
    # Addon items list their own price for the receipt breakdown, but per
    # the guide ("Price = Item unit price + Add Ons Price if any") the
    # item's own "price" must already include it — confirmed the hard way:
    # PPTEST-2/5's first run priced the item alone and Petpooja's Grand
    # Total silently excluded the addon entirely.
    "2_item_with_addon_and_tax": _order(
        f"PPTEST-{_RUN}-2",
        [{
            "item_id": "1002", "name": "French Fries", "price": 180.0 + 70.0, "qty": 1,
            "addon_items": [{"id": "2001", "name": "Thums Up (500 Ml)", "price": "70.00", "quantity": "1"}],
        }],
    ),
    "3_item_with_variation_and_tax": _order(
        f"PPTEST-{_RUN}-3",
        [{
            "item_id": "1003", "name": "Soft Drinks", "price": 80.0, "qty": 1,
            "variation_id": "3001", "variation_name": "Full",
        }],
    ),
    "4_item_with_discount_and_tax": _order(
        f"PPTEST-{_RUN}-4",
        [{"item_id": "1001", "name": "Vanilla Ice Cream", "price": 120.0, "qty": 3}],
        discount_total="50", discount_type="F",
    ),
    "5_item_with_addon_and_variation_and_tax": _order(
        f"PPTEST-{_RUN}-5",
        [{
            "item_id": "1003", "name": "Soft Drinks", "price": 80.0 + 70.0, "qty": 1,
            "variation_id": "3001", "variation_name": "Full",
            "addon_items": [{"id": "2001", "name": "Thums Up (500 Ml)", "price": "70.00", "quantity": "1"}],
        }],
    ),
}


def main() -> None:
    if not is_configured():
        print("PETPOOJA_APP_KEY/APP_SECRET/ACCESS_TOKEN/REST_ID not all set in .env — aborting.")
        sys.exit(1)

    results = {}
    for name, order in SCENARIOS.items():
        try:
            result = save_order(order, CALLBACK_URL, GST_RATE)
            results[name] = result
            print(f"{name}: OK -> {result['message']!r} (client_order_id={result['client_order_id']}, "
                  f"petpooja orderID={result['petpooja_order_id'] or '<blank in sandbox response>'})")
        except PetpoojaError as e:
            results[name] = None
            print(f"{name}: FAILED -> {e.response}")

    print("\nSummary (client order IDs — searchable in the sandbox dashboard's Order Listing "
          "page under 'Client order id' — send these back to Petpooja for review):")
    for name, result in results.items():
        print(f"  {name}: {result['client_order_id'] if result else 'FAILED'}")


if __name__ == "__main__":
    main()
