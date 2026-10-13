# WhatsApp templates, chat setup and catalogue

Everything here is generated from `app/whatsapp/templates.py`, which is the
source of truth: on every deploy the app makes Meta match it (creates
missing templates, edits changed ones, sets the welcome message, ice breakers
and / commands). Check status at `GET /api/admin/whatsapp/templates`, re-run
with `POST /api/admin/whatsapp/templates/sync`.

Ordering number: **+1 555-397-2507** (Cloud API, WABA 2546645492500823).
Kitchen alerts go to `ADMIN_PHONE` (Mom's own WhatsApp, 99406 21800).
All templates are category **Utility**, language **English (`en`)**, footer
"Tulsi Foods · pure veg · Alwarpet, Chennai" unless noted.

## Chat front door

- Welcome message: on (the bot answers the first open with the menu).
- Ice breakers: “Show me the menu” · “Track my order” · “Reorder my last order” · “Talk to the kitchen”
- Commands: /menu (See today's menu and order) · /track (Where is my order?) · /reorder (Order your last order again) · /kitchen (Ask the kitchen a question)

## Templates

### `tulsi_order_placed`

Customer, the moment the order is placed.

**Order received**

> Hi {{1}}, thank you for ordering from Tulsi Foods! 🙏
> 
> *Order #{{2}}*
> {{3}}
> *Total: ₹{{4}}*
> ⏱ {{5}}
> 
> We'll message you the moment the kitchen accepts it.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` 1 North Indian Thali, 2 Masala Chai · `{{4}}` 367 · `{{5}}` Arriving in about 45–60 minutes

### `tulsi_order_accepted`

Customer, kitchen accepted the order on the POS.

**We're cooking your order**

> Good news, {{1}}! The kitchen has accepted *order #{{2}}* and it's on the stove now 🍳
> 
> We'll tell you as soon as it's packed.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142

### `tulsi_order_ready_delivery`

Customer, food packed (delivery order).

**Packed and ready**

> Hi {{1}}, your *order #{{2}}* is packed and ready 🛍️
> 
> We're booking your rider now. You'll get the rider's live tracking link next.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142

### `tulsi_order_ready_pickup`

Customer, food packed (pickup order).

**Ready for pickup**

> Hi {{1}}, your *order #{{2}}* is ready to collect 🛍️
> 
> 📍 {{3}}
> 
> Just show this message at the counter.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` 34 Murrays Gate Road, Alwarpet

### `tulsi_rider_on_the_way`

Customer, rider booked and on the way.

**On its way**

> Hi {{1}}, your *order #{{2}}* is on its way with a Porter rider 🛵
> 
> Follow the rider live: {{3}}
> 
> Please keep your phone handy in case the rider calls.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` https://porter.in/track/AB12CD

### `tulsi_order_delivered`

Customer, delivered (fallback without the rating button).

**Delivered**

> Hi {{1}}, your *order #{{2}}* has been delivered. Enjoy your meal! 🍛
> 
> If anything wasn't right, just reply here and we'll fix it.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Sample: `{{1}}` Asha · `{{2}}` 142

### `tulsi_order_delivered_rate`

Customer, delivered, with a button to rate each dish.

**Delivered**

> Hi {{1}}, your *order #{{2}}* has been delivered. Enjoy your meal! 🍛
> 
> How was it? Tap below to rate each dish. It takes ten seconds and helps a small family kitchen a lot.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Rate your food** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 142

### `tulsi_order_cancelled`

Customer, order cancelled.

**Order cancelled**

> Hi {{1}}, your *order #{{2}}* has been cancelled.
> 
> {{3}}
> 
> Sorry about that. Reply here if you have any questions.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Sample: `{{1}}` Asha · `{{2}}` 142 · `{{3}}` Your UPI payment of ₹367 will be refunded within 2 days.

### `tulsi_payment_received`

Customer, kitchen confirmed the UPI payment.

**Payment received**

> Thank you, {{1}}! We've received ₹{{2}} for *order #{{3}}* ✅
> 
> Your food is in good hands.

_Tulsi Foods · pure veg · Alwarpet, Chennai_

Button: **Track your order** → `https://tulsifoods.app/track/{{1}}` (order's tracking token).

Sample: `{{1}}` Asha · `{{2}}` 367 · `{{3}}` 142

### `tulsi_kitchen_book_rider`

Kitchen (Mom): order accepted, book the Porter rider.

**Book a rider**

> Order #{{1}} has been accepted on the POS and needs a Porter rider.
> 
> {{2}}
> 
> Once booked, reply to this message with the Porter link and the fare.

_Swipe right on this message to reply_

Sample: `{{1}}` 142 · `{{2}}` Drop: Asha, 12 Luz Church Road, Mylapore. Phone 98123 45678. Prepaid, collect nothing.

### `tulsi_kitchen_customer_message`

Kitchen (Mom): a customer's question or file, to answer by replying.

**Customer message**

> Message from customer {{1}}:
> 
> {{2}}
> 
> Reply to this message to answer them on WhatsApp.

_Swipe right on this message to reply_

Sample: `{{1}}` Asha (+91 98123 45678), order #142 · `{{2}}` Can you make it less spicy please?

### `tulsi_kitchen_alert`

Kitchen (Mom): anything else (fallback; Meta files it as marketing).

**Tulsi kitchen alert**

> 🔔 New for the kitchen: {{1}}
> 
> Reply to this message to answer or update it.

_Swipe right on this message to reply_

Sample: `{{1}}` Order #142 accepted. Book a Porter 2-wheeler: drop Asha, 12 Luz Church Road, prepaid.

Note: Meta re-filed `tulsi_kitchen_alert` (one open variable) as MARKETING.
Kitchen alerts therefore use `tulsi_kitchen_book_rider` and
`tulsi_kitchen_customer_message`, which name the order or customer and stay
UTILITY; the generic alert is only a fallback.

## WhatsApp catalogue

Feed: **https://tulsifoods.app/whatsapp-catalog.csv**, read hourly by the
"Menu" catalogue (1768879374330631), linked to the ordering WABA with cart
and catalogue visible. Half portions are a "Half" size of the same dish;
dishes the POS can't take are out of stock; photo-less dishes use the
branded name cards (`scripts/make_catalog_cards.py`).
