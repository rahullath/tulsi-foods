# WhatsApp templates and catalogue

Meta delivers a message we start (order updates, rider link, kitchen alerts)
only as an **approved template**, unless the person wrote to the business
number in the last 24 hours. Free text is the fallback; SMS is used only when
WhatsApp is switched off, since SMS without TRAI DLT registration is dropped.
Cost: utility templates ₹0.115 each + 18% GST (India, 2026).

## They create themselves

The wording below lives in `app/whatsapp/templates.py`. On every deploy the
app finds the WhatsApp Business Account from its access token (or
`WHATSAPP_WABA_ID`) and submits any template Meta doesn't have yet, as
category **Utility**, language **English (`en`)**. Utility templates are
usually approved within minutes.

- Check: `GET /api/admin/whatsapp/templates` (admin token) lists each template,
  its Meta status, and the result of the last automatic sync.
- Re-run: `POST /api/admin/whatsapp/templates/sync`.
- If the sync reports a permissions error, the token lacks
  `whatsapp_business_management`: create the templates by hand in WhatsApp
  Manager with exactly the names and bodies below.

Until a template is approved, the code falls back to the matching Meta library
template (`order_management_1`, `order_update_1`, `order_confirmed`,
`order_pick_up_1`, `delivery_confirmation_1`, `order_delivered`,
`order_cancelled_1`) if you added it, then to plain text.

## The templates

### `tulsi_order_placed`

Customer, the moment the order is placed.

> Hi {{1}}, thank you for ordering from Tulsi Foods. Your order #{{2}} is with the kitchen: {{3}}. Total ₹{{4}}, estimated time {{5}}. We will message you when it is accepted and when it leaves.

Sample values: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` 1 North Indian Thali, 2 Masala Chai · `{{4}}` 367 · `{{5}}` about 45 to 60 minutes

Button: **Visit website**, text `Track order`, dynamic URL `https://tulsifoods.app/track/{{1}}` (sample `https://tulsifoods.app/track/k3x9p2qa`). The code fills the order's tracking token.

### `tulsi_order_accepted`

Customer, kitchen accepted the order on the POS.

> Hi {{1}}, the Tulsi Foods kitchen has accepted your order #{{2}} and is cooking it now. We will message you again when it leaves the kitchen.

Sample values: `{{1}}` Asha · `{{2}}` 142

Button: **Visit website**, text `Track order`, dynamic URL `https://tulsifoods.app/track/{{1}}` (sample `https://tulsifoods.app/track/k3x9p2qa`). The code fills the order's tracking token.

### `tulsi_order_ready_delivery`

Customer, food ready (delivery order).

> Hi {{1}}, your Tulsi Foods order #{{2}} is packed and ready. We are booking your rider now and will send the rider's live tracking link next.

Sample values: `{{1}}` Asha · `{{2}}` 142

Button: **Visit website**, text `Track order`, dynamic URL `https://tulsifoods.app/track/{{1}}` (sample `https://tulsifoods.app/track/k3x9p2qa`). The code fills the order's tracking token.

### `tulsi_order_ready_pickup`

Customer, food ready (pickup order).

> Hi {{1}}, your Tulsi Foods order #{{2}} is ready for pickup at {{3}}. Please show this message at the counter.

Sample values: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` 34 Murrays Gate Road, Alwarpet

Button: **Visit website**, text `Track order`, dynamic URL `https://tulsifoods.app/track/{{1}}` (sample `https://tulsifoods.app/track/k3x9p2qa`). The code fills the order's tracking token.

### `tulsi_rider_on_the_way`

Customer, rider booked and on the way.

> Hi {{1}}, your Tulsi Foods order #{{2}} is on its way with a Porter rider. Follow the rider live here: {{3}} and tap below for your order details.

Sample values: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` https://porter.in/track/AB12CD

Button: **Visit website**, text `Track order`, dynamic URL `https://tulsifoods.app/track/{{1}}` (sample `https://tulsifoods.app/track/k3x9p2qa`). The code fills the order's tracking token.

### `tulsi_order_delivered`

Customer, order delivered.

> Hi {{1}}, your Tulsi Foods order #{{2}} has been delivered. If anything was not right, reply to this message and we will fix it.

Sample values: `{{1}}` Asha · `{{2}}` 142

### `tulsi_order_cancelled`

Customer, order cancelled.

> Hi {{1}}, your Tulsi Foods order #{{2}} has been cancelled. {{3}} Reply to this message if you have any questions.

Sample values: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` Your UPI payment of ₹367 will be refunded within 2 days.

### `tulsi_kitchen_alert`

Kitchen (mom), porter booking card and reminders.

> Kitchen alert from the Tulsi Foods app: {{1}} Reply in this chat with the Porter tracking link and fare once booked.

Sample values: `{{1}}` Order #142 accepted. PORTER: pickup Tulsi Foods, drop Asha, 12 Luz Church Road, prepaid.

## WhatsApp catalogue

The catalogue is a data feed the app generates from the menu:
**https://tulsifoods.app/whatsapp-catalog.csv**. It has every dish, half
portions as a "Half" size of the same item, real photos where we have them and
a branded name card otherwise (`scripts/make_catalog_cards.py`), category
tags, and "out of stock" for dishes the POS can't take.

One-time setup in Meta Commerce Manager:

1. Commerce Manager → **Create catalogue** → *Online products* → name it
   "Tulsi Foods menu", owned by the Tulsi Foods business.
2. Catalogue → **Data sources** → *Add items* → **Data feed** → *Use a URL*
   → paste the feed URL → schedule **Daily**, currency **INR**.
3. WhatsApp Manager → your phone number → **Catalogue** → connect "Tulsi Foods
   menu", and turn on **Show catalogue icon in chat** and **Add to cart**.

Customers then browse the menu inside WhatsApp and send a cart. The bot
receives it, drops anything finished for today, and goes straight to checkout
(delivery or pickup, address, time, payment). Prices and dishes update by
themselves every day from the feed.
