# Tulsi Foods — System Handoff & Build Log

Last updated: 2026-08-30 (session: live order loop without Meta + verified Borzo payload).
Commits: `9b634dc` (live loop), `a6d8792` (roadmap). Branch `master`, pushed.

This document is the source of truth for anyone (or a future session) resuming the
project: what is live, why each thing exists, what is verified, and the ONE action
that still blocks production dispatch on the hosted app.

---

## 1. TL;DR — is it usable without Meta?

**Yes.** A customer can now place a real order, pay by UPI, and track it live; Mom
gets pinged on Telegram and on the admin page. No Meta verification needed.

Live loop:
customer checks out → order saved → **Telegram DM** + **admin beep** tell Mom →
Mom cooks, taps "Book rider" → **Borzo** dispatches → customer watches
`/track/{id}` → Borzo webhook marks delivered.

---

## 2. What was added and why

### 2.1 Customer status + tracking (`/track/{order_id}`) — `app/templates/track.html`, `app/main.py`
- Route `GET /track/{order_id}` (404 if missing) + a self-contained single page
  with a live status stepper (new → preparing → ready → out_for_delivery →
  delivered / cancelled), the total, items, address, and a link to live rider
  tracking once a courier exists. Polls `/api/orders/{order_id}` every 10s.
- Why: the success screen previously promised "We'll message you on WhatsApp" —
  a promise Meta wasn't fulfilling. Now the customer has a no-app status surface.
- Checkout success link updated to `/track/{id}` (`menu.html`).

### 2.2 UPI payments (static, no gateway) — `app/config.py`, `app/main.py`, `app/templates/menu.html`
- `UPI_VPA=tulsifoods@icici`, `UPI_PAYEE_NAME=Tulsi Foods`.
- `upi_uri(amount, txn_ref)` builds a standard `upi://pay?pa=&pn=&am=&cu=INR&tn=&tr=`
  deep-link. Frontend `upiLink()` in `menu.html`.
- Checkout: "Pay by UPI" option (only rendered if `UPI_VPA` set). After placing a
  UPI order, the success screen shows a **"Pay ₹{exact total} with UPI app"**
  button (amount uses the server-computed `data.total`, txn ref = order id).
- Why this flow: the exact delivery-inclusive total is only known after order
  creation, so payment is offered *after* placement (standard restaurant flow).
- Credit is **confirmed manually** by the kitchen (no gateway webhook). The
  admin/git flow treats payment_method=upi as "awaiting payment".

### 2.3 Telegram kitchen alert (no Meta) — `app/telegram.py`, `app/orders.py`, `app/config.py`, `app/static/admin.js`
- `app/telegram.py`: `notify_new_order(order)` DMs a formatted message + admin
  link; `notify_status` for later pings. Uses `TELEGRAM_BOT_TOKEN` +
  `TELEGRAM_CHAT_ID`. `enabled()` = both set.
- Hooked in `orders.create_order` (non-blocking try/except) so every new order DMs
  Mom. Verified live: bot @tulsifoodsbot, chat 8550745217.
- **Rule:** a Telegram bot can only DM a user who has pressed Start first. The
  "chat not found" error = not yet Started. Existing user must Start the bot.
- Admin fallback: `admin.js` `beepNewOrder(n)` — WebAudio beep + toast + tab-flash
  when `loadOrders()` (30s poll) sees a brand-new order id. Works without Telegram.

### 2.4 Notification dispatcher — `app/notify.py`, `app/sms/`
- `notify_status(order, status)` / `notify_dispatch(...)`: if `WHATSAPP_ACTIVE=1`
  (Meta verified) send WhatsApp template→text; else fall back to SMS via Twilio.
- `app/sms/twilio.py`: httpx sender, API-key auth. **Trial-aware:** on trial
  (`TWILIO_TRIAL=1`, default) it *skips* — trial rejects custom bodies (error
  572006) and only delivers Twilio's generic template texts to verified numbers,
  which is meaningless for customers. Flip `TWILIO_TRIAL=""` (paid account + Indian
  DLT sender) to send real SMS.
- `_send_status_whatsapp`/`_send_dispatch_whatsapp` in `main.py` and
  `_send_status_whatsapp_if_needed` in `webhooks.py` were refactored to delegate to
  `notify.*`. `webhooks.py` only notifies on delivered/cancelled (the action
  statuses) to avoid spam.

---

## 3. Borzo dispatch — payload VERIFIED against official spec

Reminder of setup: production CMS Module API token (from the OpenCart wizard) on
the **normal** account, base URL `https://robot.wefast.in/api/cms-module/1.0`,
auth header `X-DV-Auth-Token: <token>` (NOT `Authorization: Bearer`),
`payment_method=non_cash`.

`client-profile` (GET) confirms: client_id 8783680, legal_type company,
`payment_methods: ["non_cash","bank_card"]`, agreement approved. It does **not**
expose a wallet-balance field — the only real proof of funding is a successful
`create-order` (books a rider, spends wallet). User is testing this live.

Our `create_order` payload was checked field-for-field against the official
`borzo-apidocs.pdf` (§ create-order). **All field names are valid:**

Order level:
- `matter` ✓, `vehicle_type_id` (8 = motorbike ≤20kg) ✓, `total_weight_kg` ✓,
  `is_contact_person_notification_enabled` ✓, `is_thermobox_required` ✓ (valid —
  thermobox = hot box for food; distinct from `is_motobox_required`), `payment_method=non_cash` ✓, `points` ✓.

Point level (both pickup and delivery):
- `address` ✓, `contact_person.{phone,name}` ✓, `client_order_id` ✓ (=our order id,
  used to match webhooks — see below), `latitude`/`longitude` ✓, `note` ✓,
  `is_order_payment_here: false` ✓.

**Payment intent:** order-level `payment_method=non_cash` means the company (wallet/
card) funds the courier. We set `is_order_payment_here:false` and NO `taking_amount`
on the delivery point → the courier does NOT collect payment. Correct: customer pays
us separately (UPI/COD at the store), Borzo only moves food. Do not send
`taking_amount` for this setup.

**Webhook matching:** `POST /webhook/borzo` (re-pointed, secret
`BORZO_CALLBACK_TOKEN`) maps Borzo status → our order via `delivery.client_order_id`
(`app/webhooks.py:157`), which we set to our order id. Statuses map
accepted/preparing/ready/out_for_delivery/delivered/cancelled → our status.
Signature checked with `X-DV-Signature` (HMAC of raw body).

If a live `create-order` fails during testing, capture the `is_successful:false`
error JSON and compare with the doc — but the field names are already confirmed
correct.

---

## 4. Configuration (secrets live ONLY in `.env` locally + Railway vars — never in code/docs)

| var | value (redacted; see `.env`) | note |
|-----|------------------------------|------|
| UPI_VPA | tulsifoods@icici | UPI pay-to (not a secret) |
| UPI_PAYEE_NAME | Tulsi Foods | shown on pay screen |
| TELEGRAM_BOT_TOKEN | (from @BotFather, @tulsifoodsbot) | secret — see .env |
| TELEGRAM_CHAT_ID | 8550745217 | mom's chat (was test 7552410176) |
| BORZO_AUTH_TOKEN | (CMS Module API token) | secret — see .env |
| BORZO_BASE_URL | https://robot.wefast.in/api/cms-module/1.0 | |
| BORZO_CALLBACK_TOKEN | (webhook secret) | secret — see .env |
| TWILIO_* | set | trial (TWILIO_TRIAL=1) → SMS skips |
| WHATSAPP_ACTIVE | (empty) | flip to 1 post-Meta for WhatsApp |

⚠️ **Never put real tokens in this doc or any committed file.** Copy the actual
values from the local `.env` when setting Railway vars.

---

## 5. ⚠️ THE deployment action that still blocks hosted production

Code is pushed to GitHub (`master`); **Railway deploys from git**. But Railway
**env vars are NOT code** — they must be pasted in the Railway dashboard
(`tulsifoods.app` → Variables). Until added, the hosted app has no `UPI_VPA`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and the new defaults in `config.py` mean
UPI/Telegram stay hidden/off in production even though local `.env` is correct.

Set these in Railway (mirror `.env` locally — **use the real values from your local
`.env`, never paste secrets here**):
```
UPI_VPA=tulsifoods@icici
UPI_PAYEE_NAME=Tulsi Foods
TELEGRAM_BOT_TOKEN=<from local .env>
TELEGRAM_CHAT_ID=8550745217
BORZO_AUTH_TOKEN=<from local .env>
BORZO_BASE_URL=https://robot.wefast.in/api/cms-module/1.0
BORZO_CALLBACK_TOKEN=<from local .env>
```
Then redeploy (Railway auto-builds on push; set vars then re-deploy).

---

## 6. Open / pending

- **Borzo live dispatch** — user testing now that wallet funded. Verified payload.
- **Petpooja relay** — awaiting staging creds from Malvi (kitchen-first POS path).
- **Meta / WhatsApp** — `WHATSAPP_ACTIVE` still off; WhatsApp long-term channel,
  SMS trial (skips), Petpooja + tracking primary for now.
- **Mom's Telegram chat** — currently 8550745217; swap if she uses a different
  account.

---

## 7. Where things live (map)

- `docs/ROADMAP.md` — future: Telegram mini-app, SEO headings, "Order Now" CTAs,
  orphaned `/bio`.
- `docs/META_CONTINGENCY_PLAN.md` — Meta fallback strategy.
- `app/templates/track.html`, `app/telegram.py`, `app/notify.py`, `app/sms/`,
  `app/delivery/borzo.py`, `app/config.py`, `app/static/admin.js`, `app/orders.py`,
  `app/main.py`, `app/webhooks.py`.
