# WhatsApp templates (customer + kitchen messages)

Meta delivers a business-initiated message only as an **approved template**
unless the person messaged the business number in the last 24 hours. So every
message we start (order updates, rider link, delivery fare, kitchen alerts) is
a template. Free text is only the fallback, and SMS is used only when WhatsApp
is switched off (`WHATSAPP_ACTIVE` unset), because SMS without TRAI DLT
registration is dropped silently.

Cost: utility templates ₹0.115 each + 18% GST (India, 2026).

## Library (pre-approved) vs custom templates

WhatsApp Manager's **template library** (Utility: Default / Calling;
Authentication: OTP) has pre-written templates that are approved instantly
because only the variables and buttons can be changed. The order-status ones
the code uses (`order_management_1`, `order_update_1`, `order_confirmed`,
`order_pick_up_1`, `delivery_confirmation_1`, `order_delivered`,
`order_cancelled_1`) are library templates. Library templates are created in
**English (US)** (`en_US`); the code now tries `en_US`, `en` and `en_GB`
automatically and remembers which one works.

Custom templates (`delivery_fare`, `rider_on_the_way`, `kitchen_alert`) need
Meta's review, usually minutes to a day for Utility.

### `order_management_1` (library, order confirmation)
Sent the moment a customer places an order:
"Hi {{1}}, Thank you for your {{2}}! Your order number is {{3}}. We'll start
getting {{4}} ready to ship. Estimated delivery: {{5}} …"
The code fills: customer name · `order` · `#42` · items (e.g. `1 North Indian
Thali, 2 Masala Chai`) · estimated time (e.g. `about 45 to 60 minutes`).
Button: set the "View order details" website URL to `https://tulsifoods.app/track`.

## Check them against the code

Set `WHATSAPP_WABA_ID` on Railway (WhatsApp Business Account ID, shown in
WhatsApp Manager and Business settings). Then open
`/api/admin/whatsapp/templates` with the admin token: it lists every template
the code sends, whether Meta has it approved, in which language, and whether
the number of variables matches. Any row with `"ok": false` needs fixing.

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
