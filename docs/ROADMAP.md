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

### R2-1. Finalize the delivery flow (testing phase) — `[~]`
- `[x]` **Lunch / Dinner windows, not rigid 12:30.** Checkout now offers a window
  (Lunch 12:00–2:30 PM, Dinner 6:30–9:30 PM) plus "As soon as possible"; the
  pill sets a reference time (`scheduled_at`) and stores `scheduled_window` on
  the order. Confirm message, Telegram kitchen alert, tracking page, and `ensure
  it's labelled by window`. Monday morning rejects the Lunch window (opens 14:00)
  and points people to Dinner. Parser hardened against `Z`/offset combos.
- `[~]` **Pay-courier-direct option.** `pay_courier_direct` on the order:
  delivery-fee quote is recorded but excluded from the total the customer owes
  us; checkout shows "pay the rider directly", confirm line says so, kitchen.js
  card states "rider collects the ₹X delivery fee", tracking page flags it.
  Remaining: reconcile with Mom's actual rider practice + the test pass.
- `[x]` **Orders only during open hours.** ASAP orders were possible 24/7; the
  schedule gate now checks the full weekly-hours table (Mon opens 14:00, others
  09:00, Sun 11:00; close 21:00) for both ASAP (now) and scheduled times, with
  copy pointing to the next window when closed. Monday morning still refuses
  the Lunch window specifically. (TZ math in the ISO parser fixed as part of it.)
- `[ ]` **Test pass over the whole order path**: quote → order create → confirm
  msg → rider dispatch → track statuses → delivered. Fix edge cases found (e.g.
  quote cache key, pin-drag re-quote).

### R2-2. Mobile navigation — `[x]`
One shared `_nav.html` partial rendered from `base.html`: canonical desktop
links (Categories dropdown global — `categories` added to every public route
context; single "Order online" CTA) + burger button opening a panel with the
same links + category list on ≤768px. Deleted the 6 copy-paste nav blocks and
their inline CSS (nav CSS now lives in the partial itself, since most pages
skip `style.css`); stripped the duplicated brand rows on /menu (search kept)
and item pages. Kitchen/admin pass `hide_nav`. Drive-bys: category pages link
/track, 404 links Our story. Active page highlighted via `request.url.path`.
Verified: 23 pages render, burger present everywhere public and absent on
tools, inline JS clean, link-graph shows every page reaches the core links.

### R2-3. Footer reformat — `[x]`
One shared `_footer.html` partial rendered from `base.html` (same self-contained
pattern as the nav — most pages skip `style.css`). Content is the union of what
the 10 per-template footers carried: address/hours, category links, the full
link set, and the also-known-as / also-on entity line — so track, privacy,
refund and item/menu pages gain category + entity links they never had.
Kitchen/admin hide it via the existing `hide_nav` flag. Deleted all per-template
footer markup + CSS (`.footer`, `.mf`, `.bio-footer`). Verified: 24 pages render,
exactly one footer everywhere public, none on tools, inline JS clean. (Note:
`index.html` still has its own footer block but is unrouted — dead template,
cleanup candidate for R2-12.)

### R2-4. "Fresh from the Kitchen" compilation page (`/updates`) — `[x]`
Not a diary (nobody will update it daily) — a compilation of Instagram posts,
WhatsApp statuses and kitchen announcements that makes the site look deeper
to crawlers: `data/updates.json` (date, kind, title, text, optional dish photo,
dish links, source URL) renders cards with `Blog`/`BlogPosting` JSON-LD,
internal links to dishes and pages, plus `/updates.xml` RSS and sitemap
lastmod that follows the data file so new entries bump freshness without a
deploy. Seeded with 4 honest entries from shipped facts (11 years, direct
ordering, windows, tracking). Linked from the landing "Latest updates" teaser
+ every footer + llms.txt. To add a post: append one JSON entry, done — photo
and dish references are validated so typos can't break the page.

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
