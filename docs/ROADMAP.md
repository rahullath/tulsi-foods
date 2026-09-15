# Tulsi Foods — Product Roadmap (non-Meta)

Committed & pushed: `9b634dc`. This doc captures planned improvements that are
**independent of Meta verification** and can ship step-by-step. Each section is
scoped with concrete edits so it's buildable without re-discovery.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Round 2 — Sep 2026 backlog (from owners' notes)

Long-term **why**: Tulsi Foods should become the working model of a small
business that self-sustains without delivery-platform commissions — direct
ordering, own riders/courier, no aggregator markup. Every change below should
be judged against "does it remove pure-logistic friction or outdated process"
rather than "does it optimize Mom's routine".

Shipped this round (commit `ede04c1` + follow-ups):
- `[x]` /track entry page (reference + phone lookup), /category/{slug} pages for
  all 10 groups, branded 404 in sitemap, nav/footer/sitemap interlinking, all
  item↔category links bidirectional — no orphaned pages (audited).
- `[x]` Floating **"View cart"** bar fixed to bottom on every page (in
  `base.html`), reads `tulsi_menu_cart`, totals via `/api/menu`, hides on `/menu`
  (full checkout there) and when empty.
- `[x]` Checkout no longer inflates totals with a fake `~₹45–₹100`: until an
  address/pin gives a live Borzo quote, delivery shows "Live rate" and is
  excluded from the total.
- `[x]` "Pickel" → "Pickle" typo fixed in `data/menu.json`.
- `[x]` `llms.txt` expanded: categories, popular dishes, tracking page, 11-year
  note; data-driven from the menu so it can't drift.
- `[x]` Category pages: curated per-category intro copy + "Bestsellers" strip.
- `[x]` Hero badge → "11 YEARS · MYLAPORE · PURE VEG".
- `[x]` Repo junk: removed tracked `spec.v1.bak.md`; moved `pay/cashfree-agent-skills.md`
  → `docs/`. `media/`, `design/`, `seo/`, CSVs, DBs already gitignored.

### R2-1. Finalize the delivery flow (testing phase) — `[ ]`
- **Lunch / Dinner windows, not rigid 12:30.** Repace the single scheduled time
  with two order windows (e.g. Lunch 11–2, Dinner 6–9:30) in checkout + confirm.
  Touch: `app/orders.py` `MAX_SCHEDULE_AHEAD`/`scheduled_at` handling, menu.html
  time picker, admin/kitchen display, config `OPENING_HOURS`.
- **Pay-courier-direct option.** Separate "Order total" (food + packing + GST)
  from "Delivery fee", let customer choose pay-rider-in-cash (delivery_fee not
  added to total, still recorded on the order for reconciliation) vs pay-us.
  Confirm message must say "pay the rider ₹X directly".
- **Test pass over the whole order path**: quote → order create → confirm msg →
  rider dispatch → track statuses → delivered. Fix edge cases found (e.g. quote
  cache key, pin-drag re-quote).

### R2-2. Mobile navigation — `[ ]`
No nav on mobile at all (all navs are `display:none` under 768px). The fixed
cartbar helped, but browsing to categories/track/delivery from a phone is still
awkward.
- Add a compact top nav visible on mobile: brand + burger → panel with Menu,
  Categories dropdown, Delivery, Track, About, Contact, Order.
- Each template duplicates its nav — extract a shared `app/templates/_nav.html`
  include + `_nav.css` block in `base.html` once, then have every page use it
  (removes the 8 copy-paste navs). Same for the footer (R2-3).

### R2-3. Footer reformat — `[ ]`
Footers are per-template and slightly different. Unify: one `_footer.html`
include with ordered link groups (Order: Menu/Categories; Help: Track, Delivery,
FAQs; Company: Our story, Contact, Privacy, Refund; Legal) + address/hours.
Build on the base.html include approach from R2-2.

### R2-4. Daily "journal / feed" page (Instagram repost for recrawl) — `[ ]`
A `/journal` (or `/updates`) page that embeds/posts the day's Instagram content
+ monthly offers — nobody has to read it, but it changes daily and forces a
re-index, and it should look nice (it's also a social-proof surface).
- Decide engine: manual (mom posts → we paste a link/photo in an admin textarea)
  vs semi-automated (jsonl entries via admin form). Keep it dead-simple; a
  file-backed `data/journal.json` with date, image, caption, offer.
- Template mirrors the landing style; add `?p=1`-style pagination + RSS/atom + a
  `<link rel=alternate type=application/rss+xml>` in base for the bots.
- Emergency: if hero image (R2-5) isn't ready, this page can host kitchen
  everyday shots.

### R2-5. Hero image → Mom & staff / restaurant interior — `[ ]`
Needs a real photo asset (not available yet). Wire once supplied: replace
`/static/img/landing-hero.jpg` on landing hero + `about.html` story photo, and
add `alt`/JSON-LD `image` updates. Also crop from `media/` if Mom picks one.

### R2-6. Category pages: reviews-backed descriptions + nutrition profiles — `[ ]`
- **Comprehensive descriptions from real data**: pull featured reviews per
  category (reviews table currently empty locally — populate from Google/
  Swiggy reviews; `reviews.list_featured_reviews` exposed already) and render
  quoted pull-quotes on category + item pages ("We'll never say reviewer lies").
- **Nutrition estimates**: Swiggy's are fake; publish better *estimates* (cal,
  protein, fiber, portion) — good for Google knowledge panels, Gemini/AI
  recommenders, and trust. Schema: `Recipe`/`Offer` with `nutrition["nutrition"]`+LD.
  Keep clearly labelled "approximate, kitchen-made to order".

### R2-7. Discounts / promo codes — `[ ]`
Small engine: `discounts` table (code, type flat/pct, min_subtotal, active,
stackability), applied at checkout, reflected in order total + confirm message,
and shown on a `/offers` page + journal. Scope as phase 1 (single code, no
stacking) then review.

### R2-8. "11 years of Tulsi Foods" theme — `[ ]`
Sept 2026 = 11 years → use as legit reason the site exists: hero badge done,
but extend to a story strip ("Why we started this instead of Swiggy/Zomato" →
commissions), a `/story` or on-landing section, footer line, and pinned journal
entry. Positioning: the anti-commission, self-sustaining small-business model.

### R2-9. Dine-in QR ordering (table number → Petpooja, not WhatsApp) — `[ ]`
Table-place QR → lightweight menu/order submission bound to a table number →
goes into Petpooja POS directly (unlike web/WhatsApp orders). Do NOT build
until: (a) Petpooja prod creds are issued, (b) we observe how Mom's current
dine-in order-taking actually works (see R2-10) — the flow may be better served
by paper + a quick tablet entry than a customer-facing QR.

### R2-10. Local customer-flow research — `[ ]`
People behave weirder than data predicts. Before R2-1/R2-9, spend time in the
restaurant observing: how orders are taken by phone/table/counter, what gets
repeatedly asked, where "logistical friction" hides. Capture into a living
doc (`docs/CUSTOMER_FLOW_NOTES.md`) feeding the checkout/confirm/menu copy.
No code until observations exist.

### R2-11. SEO as standing practice, not ad-hoc — `[ ]`
The recurring ask "why do I have to think of this?" is fair: build a checklist
doc (`docs/SEO_PLAYBOOK.md`) that each page/feature must pass by default
(canonical, h1-unique, meta-desc, breadcrumb, JSON-LD type, sitemap entry,
inbound links — no orphans). Reviews the new /journal, category, and 404 pages
against it; extend with keyword intents ("Tulsi Foods menu price", "pav bhaji
near Mylapore", "Jain food Mylapore").

### R2-12. Repo restructure — `[ ]`
Done so far: junk removal + `docs/` home for agent/misc notes. Deeper rebuild
(defer; low ROI now): consolidate `app/` subpackages (`delivery/`, `whatsapp/`,
`sms/`, `petpooja/`) docs → `docs/`, split `main.py` (>1k lines) into routers.

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
