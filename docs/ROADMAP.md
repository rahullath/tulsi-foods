# Tulsi Foods — Product Roadmap (non-Meta)

Committed & pushed: `9b634dc`. This doc captures planned improvements that are
**independent of Meta verification** and can ship step-by-step. Each section is
scoped with concrete edits so it's buildable without re-discovery.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## 1. Telegram mini-app (Kitchen Console) — long-term

Goal: give Mom a dedicated, zero-friction kitchen interface inside Telegram so
she never has to keep a browser tab open. Replaces/supplements the admin beep.

Why Telegram mini-app over a web admin: Telegram Mini Apps are webviews opened
from a message button — no separate login, already authenticated to the bot, push
notifications built-in, and runs on her phone/tablet without a browser.

- **[ ]** Build a `/kitchen` web route (reuse admin logic) that works **without**
  the admin-password header — instead authenticates via `X-Telegram-User-Id`
  header Telegram sends to registered Mini Apps; allow-list `TELEGRAM_ADMIN_IDS`.
- **[ ]** Register as a Mini App via @BotFather (`/newapp` or Bot Settings →
  Mini App → link `https://tulsifoods.app/kitchen`). Bot has `has_main_web_app:true`
  already (verified via getMe).
- **[ ]** Add a persistent **menu button** on @tulsifoodsbot → opens `/kitchen`.
- **[ ]** Kitchen views: Today's orders (live), tap an order → status stepper +
  "Food ready → book rider" (calls existing `/api/admin/orders/{id}/dispatch`),
  UPI-payment confirmation toggle (mark a UPI order paid).
- **[ ]** Instead of just a text DM, send orders as an **inline-keyboard message**
  ("Order #12 · ₹445 · [Prepare] [Start cooking] [Book rider]") so Mom can act
  straight from the chat. Requires a callback handler (`callback_query`) on the bot.
- **[ ]** No webhook needed: the bot currently is poll-free on our side (we only
  *send* via bot API). For callbacks we'd add `setWebhook` → `POST /telegram` or a
  forever-poll task. Prefer webhook.

Considerations: Mini Apps aren't "Meta-dependent" so this is safe. Effort is
moderate; the highest value is the inline-keyboard action ordering — that's what
removes the "open admin" step entirely.

---

## 2. SEO fixes — headings + meta

Grounded in a scan of `app/templates/*.html` (h1/h2/meta on each page):

| file | h1 | h2 | meta-desc | meta-keywords | gap |
|------|----|----|-----------|---------------|-----|
| index.html | 1 | 1 | **0** | 0 | missing description |
| menu.html | **0** | 1 | 1 | 0 | **no H1** (worst offender) |
| landing.html | 1 | 5 | 1 | 0 | fine |
| about.html | 1 | 2 | 1 | 0 | fine |
| bio.html | **0** | 4 | 1 | 0 | no H1 **+ orphaned** (no inbound links) |
| delivery.html | 1 | 0 | 1 | 0 | fine |
| privacy.html | 1 | 8 | 1 | 0 | fine |
| track.html | 1 | 0 | 1 | 0 | fine |
| admin.html | 0 | 0 | 0 | 0 | noindex needed |

- **[ ]** `menu.html`: add a single `<h1>Menu & Prices — Tulsi Foods, Mylapore</h1>`
  as the page's primary heading (currently only group `<h2>`s). Add
  `<meta name="description">` (base provides one, but it's the generic homepage
  copy — override with menu-specific text).
- **[ ]** `index.html`: add `<meta name="description">`. Note index and menu look
  near-identical but index is the served `/` — confirm which is canonical via
  `@app.get("/")` and pick ONE, then `rel=canonical` the other to avoid dup pages.
- **[ ]** `bio.html`: add an `<h1>`. **It's currently orphaned** — route exists
  (`main.py:170`) but no other page links to `/bio`, so it gets no crawl/nav juice.
  Decide: link it from the homepage/menu footer + `about.html`, or fold its content
  into `about.html` and delete the route. Don't leave it silent.
- **[ ]** `admin.html`: add `<meta name="robots" content="noindex,nofollow">` so
  the kitchen admin never enters search.
- **[ ]** Optional: `JSON-LD` Restaurant schema is already built (`menu_schema`,
  `build_menu_schema`) — verify it includes `telephone`, `address` (34 Murrays Gate
  Road, Alwarpet, 600018), `servesCuisine`, `geo` (PICKUP_LAT/LNG), `openingHours`,
  `hasMenu`. Rich-result eligibility needs markup, location, and a verified
  Business Profile.
- **[ ]** Meta keywords are largely ignored by Google — treat as low-value
  garnish; the description + headings + schema are what matter. Don't overinvest.

---

## 3. "Order on WhatsApp" → "Order Now" (stop sending users to a dead chat)

Current problem: CTAs say "Order direct on WhatsApp" and the checkout nudge sends
people to `wa.me/919940062840`, but WhatsApp answers are unreliable while Meta
verification/`WHATSAPP_ACTIVE` are off — a user lands on a chat that may not get a
timely reply. Today the site already has a **real** on-site order flow, so the
WhatsApp CTAs are misleading.

Fix: reposition WhatsApp as optional "talk to us" support, and make the on-site
flow the primary ordering path.

- **[ ]** Change base/meta + landing copy from "Order on WhatsApp" →
  "Order online for delivery or pickup in Alwarpet".
- **[ ]** `menu.html` / `landing.html` / `index.html`: point the primary CTA to
  `#checkout` / `/menu` (on-site cart), *not* `wa.me`.
- **[ ]** Keep WhatsApp only as a support/fallback link (e.g. "Message us on
  WhatsApp" beside order issues), labelled clearly so it's not implied as the
  ordering channel.
- **[ ]** Once `WHATSAPP_ACTIVE=1` (post-Meta), add a "Get updates on WhatsApp"
  opt-in that actually works — until then prefer the tracking page as the status
  surface.

---

## 4. Staging / config hygiene (cheap wins)

- **[ ]** Railway env: add `UPI_VPA=tulsifoods@icici`, `UPI_PAYEE_NAME=Tulsi Foods`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (Mom's once ready), plus the existing
  BORZO/TWILIO vars. Code has defaults, but Railway overrides env.
- **[ ]** `.env` is gitignored and holds secrets (Twilio, Borzo, Telegram tokens) —
  never commit. (Already confirmed not in `git status`.)
- **[ ]** Bot: switch Mom's `TELEGRAM_CHAT_ID` from the current test id (`7552410176`)
  to her chat id once she Starts the bot.

---

## Backlog / parked

- **Petpooja relay** — awaiting staging creds from Malvi (two-way POS like
  Swiggy/Zomato; the kitchen-first path).
- **Borzo live dispatch** — needs wallet balance (`non_cash` payment configured,
  token valid; only funding blocks `create-order`).
- **SMS** — Twilio stays trial (skips, 572006); real SMS only worth it post-upgrade
  + DLT sender, and it's more expensive than WhatsApp.
- **WhatsApp mini flow** — once verified, the in-conversation service reply is free,
  making it the long-term channel (see `docs/META_CONTINGENCY_PLAN.md`).
