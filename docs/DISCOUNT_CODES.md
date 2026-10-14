# Discount codes

Codes live in the database, so you can add, pause or expire them without a deploy.
Customers enter them under **Have a discount code?** at the last checkout step, or by typing the code in WhatsApp when they see the order summary.

- The discount comes off the food subtotal. Packing, GST and delivery are then worked out on the reduced amount.
- The order is re-checked when it's placed, so an expired or already-used code can't slip through.
- A cancelled order doesn't use up the customer's code.
- The Petpooja POS receives the discount under the code's name, and the POS total matches ours.

## TRIAL15 (created automatically)
15% off, capped at ₹100, once per customer (matched by phone number).

## List codes and how often each was used
```
curl -H "X-Admin-Token: $TULSI_ADMIN_TOKEN" https://tulsifoods.app/api/admin/discount-codes
```

## Create or change a code
```
curl -X POST https://tulsifoods.app/api/admin/discount-codes \
  -H "X-Admin-Token: $TULSI_ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"code": "DIWALI50", "kind": "flat", "value": 50, "min_subtotal": 300,
       "once_per_customer": true, "expires_at": "2026-11-05", "note": "Diwali flyer"}'
```

| Field | Meaning |
|---|---|
| `kind` | `percent` or `flat` (rupees) |
| `value` | 15 means 15% (percent) or ₹15 (flat) |
| `max_discount` | Cap in rupees for percent codes |
| `min_subtotal` | Minimum food total needed to use the code |
| `once_per_customer` | One use per phone number (default true) |
| `first_order_only` | Only for customers with no earlier orders |
| `max_uses` | Total uses across everyone; leave out for unlimited |
| `expires_at` | `2026-11-05` means it works through that whole day (IST) |
| `active` | `false` pauses the code |

To pause a code, post it again with `"active": false`. Include the other fields too, because posting replaces the whole code.
