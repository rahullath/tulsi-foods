# WhatsApp templates (customer + kitchen messages)

Meta delivers a business-initiated message only as an **approved template**
unless the person messaged the business number in the last 24 hours. So every
message we start (order updates, rider link, delivery fare, kitchen alerts) is
a template. Free text is only the fallback, and SMS is used only when WhatsApp
is switched off (`WHATSAPP_ACTIVE` unset), because SMS without TRAI DLT
registration is dropped silently.

Cost: utility templates ₹0.115 each + 18% GST (India, 2026).

## Create these in WhatsApp Manager

Category **Utility**, language **English (en)**, name exactly as below. Meta
rejects a body that starts or ends with a variable, or has a variable with no
text between it and the next one, so keep the wording around them.

### `delivery_fare` (new, required)
Sent when Mom forwards the Porter link + fare. Code: `app/notify.py`.

> Hi {{1}}, your rider for Tulsi Foods order #{{2}} is booked. The delivery charge is ₹{{3}}, the actual Porter fare with nothing added. Track your rider and pay the delivery charge by UPI here: {{4}} Thank you for ordering direct.

Sample values for review: `Priya`, `42`, `86`, `https://tulsifoods.app/track/Y2BV2HUT`

### `rider_on_the_way` (new, required)
Sent when a rider is booked but the fare isn't known yet.

> Hi {{1}}, your Tulsi Foods order #{{2}} is on its way. Track your rider here: {{3}} Thank you for ordering direct.

### `kitchen_alert` (new, for Mom; set `KITCHEN_WA_TEMPLATE=kitchen_alert`)
> Kitchen alert: {{1}} — Tulsi Foods

The variable is the whole Porter booking card on one line (newlines are
flattened to " | " automatically).

## Already referenced by the code (check they are approved)

| Template | When | Variables |
| --- | --- | --- |
| `order_update_1` | POS accepts the order | name, order no. |
| `order_confirmed` | Food ready (delivery) | name, order no. |
| `order_pick_up_1` | Food ready (pickup) | name, order no., pickup address |
| `delivery_confirmation_1` | POS marks it dispatched | name, order no. |
| `order_delivered` | Delivered | name, order no. |
| `order_cancelled_1` | Cancelled | name, order no., refund ₹ |

If a template is missing or not approved, the code logs
`template <name> failed … (not approved yet?)` in Railway and falls back to
plain text, which only arrives if the customer messaged us in the last 24 h.
