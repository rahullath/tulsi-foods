# Tulsi Foods — Product Roadmap (non-Meta)

Committed & pushed: `9b634dc`. This doc captures planned improvements that are
**independent of Meta verification** and can ship step-by-step. Each section is
scoped with concrete edits so it's buildable without re-discovery.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Round 3 — Sep 2026 (owner's priorities, current — read this first)

Long-term goal restated by the owner: make this a genuinely useful tool that
works end-to-end for a non-tech-literate customer base, confidently
shareable by Mom, and eventually a **template other small restaurants can
use to leave Swiggy/Zomato** — a model that profits the restaurant and
customer, not just the aggregator. Long game; ship in order below, clean up
and document only after the app has been live and used for a while.

### UX / core flow
- `[x]` **Persist cart + customer details across the session.** Done
  2026-09-19 (`7e0984c`) — checkout details (name/phone/address/schedule/
  pin) persist to `localStorage` separately from the cart, restored on
  reopen or reload, cleared only on a successful order. Verified live.
- `[~]` **Improve cart & checkout flow generally** — the big piece of this
  landed 2026-09-19 (`3ece12f`): inline +/− quantity edit directly in the
  checkout summary (design v-final screen 1c direction), synced with the
  menu grid's steppers, closes the panel if the cart empties out. Open-
  ended item, keep revisiting for friction as it comes up.
- `[x]` **Delivery fee messaging, rewritten.** Done 2026-09-19 (`7e0984c`):
  `pay_courier_direct` now defaults `True` (customer pays the rider
  directly, fee excluded from the total) instead of bundling a zone-based
  estimate in by default; opting the other way is now framed as "we
  collect it and pay the rider for you."
- `[x]` **Checkout order-type/payment as tap-tiles.** Done 2026-09-19
  (`c9bb46c`): replaced the `<select>` dropdowns for order type
  (delivery/pickup) and payment method (COD/UPI) with tap-tile buttons,
  matching the "Final Site" mockup and the existing schedule-time tile
  pattern. Found and fixed a real bug along the way: the schedule tiles'
  click handler swept the whole checkout overlay for `.time-pill`
  elements, so clicking any tile wiped active state off the other groups
  (they now share that class for visual consistency). Scoped the sweep to
  `#time-pills`. Verified live — reload-restore path and live-click path
  both confirmed with no cross-contamination.

### Payments — "how does Mom actually get paid"
- `[ ]` **Payment confirmation, not just a UPI deep link.** `upiLink()` in
  `menu.html` already builds a `upi://pay?...&am=<exact amount>&tr=<order
  id>` intent link — the "QR with a specific amount" ask is functionally
  already there (tapping opens GPay/PhonePe pre-filled). What's missing is
  **confirmation that the money actually arrived** — right now it's an
  honor system. Look at a real payment gateway for server-side
  confirmation/webhooks. **Cashfree ruled out (2026-09-19)**: requires
  company KYC docs (CIN/GST-registered entity docs) a sole proprietorship
  doesn't have, unless their onboarding budges on that — not promising.
  Need a gateway that actually onboards sole proprietors on individual
  PAN + bank account (worth checking Razorpay Payment Links, Instamojo,
  PhonePe/Paytm Business — verify each one's KYC tier before assuming).

### SEO
- `[~]` **Standing priority, not a one-off.** 2026-09-19 (`2d94dd8`):
  reposted 18 real Instagram captions (the ones with actual content — 9
  with no caption at all were skipped rather than padded) to `/updates`,
  flowing automatically into the existing Blog JSON-LD and RSS feed, no
  new code needed. Keep auditing per `docs/SEO_PLAYBOOK.md` — this is the
  primary growth lever, always worth another pass.

### Petpooja / Admin
- `[ ]` **Pull pricing/menu from the Petpooja push, not `data/menu.json`.**
  The Menu Trigger webhook already caches the real pushed catalogue at
  `data/petpooja_menu_raw.json` (used today only for item-ID reconciliation
  in `app/petpooja/catalog.py`) — make it the actual source of truth for
  prices/availability shown on the site, not just an ID-mapping lookup.
  Check whether the last push actually persisted (Railway volume is
  confirmed mounted at `/data` — see chat history) before assuming it's
  gone.
- `[ ]` **Every Petpooja→us callback must be bulletproof.** The
  Online-Orders-queue issue is now resolved (`PETPOOJA_REST_ID` fix,
  2026-09-19 — see `docs/PETPOOJA_INTEGRATION.md`), so admin really is
  now *driven by Petpooja* live (accept/food-ready/dispatch/cancel all
  arrive as webhooks) — this item just got a lot more load-bearing. Audit
  `app/webhooks.py`'s handlers so nothing 500s or silently drops a
  callback. This is the primary admin surface now; it can't be flaky.

### Delivery / rider tracking (currently "a random hope kinda thing")
- `[ ]` **Untested end-to-end.** Needs real exploration, not just code
  review:
  - Surface live rider status to the *customer* on `/track/{token}` (not
    just our internal status enum) — pull whatever Petpooja's rider-status
    relay / Borzo webhook actually gives us.
  - Give Mom visibility into whether a booked rider will actually show,
    with enough lead time to arrange a backup.
  - A way to **override/reassign** a delivery if the assigned rider
    flakes — right now there's no manual escape hatch once
    `dispatch_rider()` has committed to a provider.

### Growth / marketing infra
- `[ ]` **Print flyers** for Mom to slip into existing Swiggy/Zomato
  orders, pitching the direct-order site to those same customers. First
  attempt 2026-09-19 rejected by the owner ("this flyer sucks") — worth a
  fresh direction next time rather than iterating on that draft. Note
  from that attempt worth keeping: the `/f?c=...` QR redirect + scan-
  logging infra already exists
  and works (`app/qr.py`, `qr_scans` table) — no auto-discount mechanism
  behind it though, so don't print a QR promising a discount that isn't
  wired up (see the discount-infra item below).
- `[ ]` **Real discount infrastructure**, replacing the hardcoded DIRECT10
  WhatsApp-only promo (see Archived below): UTM-tagged QR codes that both
  deep-link into the web-app *and* auto-apply a discount, redeemable once
  per device (needs a device-fingerprint or localStorage-flag check, not
  bulletproof but good enough to deter casual reuse). This is roadmap §7
  ("Discounts / promo codes") done properly, QR-first. Genuinely blocking
  the flyer item above from making an honest discount claim.
- `[~]` **PWA / installable web app.** Installability shipped 2026-09-19
  (`3ece12f`) — manifest, service worker (deliberately minimal: only
  caches the static logo/icon shell, never `/menu`/`/api/*`/checkout,
  since stale cached pricing on a live ordering site is a real risk),
  192/512 icons generated from the existing logo, `start_url=/menu`. What's
  still open: a bespoke condensed "app shell" home screen (design v-final's
  Home mockup, confirmed by the owner as the PWA-launch view, not a
  landing-page replacement) — deferred as its own template build, not
  done yet. Right now `start_url` just launches into `/menu`.
- `[ ]` **Loyalty mechanic** — e.g. every N orders (with a minimum order
  value) earns a free item. Explicitly framed by the owner as standard
  marketing-incentive theater, not a real value driver — keep it cheap to
  build, don't over-invest.

### Reviews / Testimonials + order recoverability
- `[ ]` **Review system**: collected per-order, surfaced on a
  Testimonials/blog-style page (extend `/updates`?), with an admin way to
  hide/delete bad-faith reviews.
- `[x]` **Fix the "customer loses their order" gap.** Done 2026-09-19
  (`e9f8a9e`) — `/track` rebuilt as "My Orders" (design v4 screen 1f):
  device-local order history (no login, no reference number), each order
  fetched live by token so status is always current, "Track this order" /
  "Order again" per card, phone-lookup kept as the fallback for a new
  device. Also found and fixed a real bug while building this: the phone
  lookup was silently broken (checkout stored digits with no
  country-code normalization while the lookup hardcoded `+91`) — fixed at
  both the write (`orders._normalize_phone`) and read (`db.py`) side, the
  latter tolerant of the already-inconsistent legacy data. SMS-the-link-
  automatically is still not done — Twilio stays trial-mode, low priority.

### Support
- `[x]` **WhatsApp chat-bubble widget.** Done 2026-09-19 (`7e0984c`) —
  moved from `landing.html`-only into `base.html`, so it's a persistent
  floating button (`.site-wa`) on every public page, hidden on
  `/admin`/`/kitchen` via the existing `hide_nav` flag. No WhatsApp
  Business API involved, that's a separate (Meta-gated) thing.

### Explicitly NOT a priority right now
- Telegram bot — **no further work planned.** It was a stopgap while
  Petpooja wasn't live; Petpooja should be done within days. Don't spend
  time here.

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

### R2-9. Dine-in QR ordering (table number → Petpooja, not WhatsApp) — `[x]`
Sandbox integration done + verified end-to-end on the live server (order 15:
Save Order → accept → callback flips `new → preparing → ready`). Full status
in `docs/PETPOOJA_INTEGRATION.md`. **Static-IP blocker RESOLVED 2026-09-17**
via the Squid proxy (`35.209.244.171`, verified from Railway — see
`docs/PETPOOJA_PROXY_MIGRATION.md`); **production credentials issued**
(restID `84713`, prod endpoints on `pponlineordercb.petpooja.com`).
**Remaining before go-live:** (a) Squid acl for prod host + prod endpoint
env vars on Railway + one real smoke order (§0/§3.7 + migration doc Stage C),
(b) menu ID reconciliation vs their real catalog (§3.2), (c) wire admin
kitchen cancel → `cancel_order()` (§3.1 tablet path). Dine-in QR flow itself
still pending (see R2-10).

### R2-10. Local customer-flow research — `[ ]`
People behave weirder than data predicts. Before R2-1/R2-9, spend time in the
restaurant observing: how orders are taken by phone/table/counter, what gets
repeatedly asked, where "logistical friction" hides. Capture into a living
doc (`docs/CUSTOMER_FLOW_NOTES.md`) feeding the checkout/confirm/menu copy.
No code until observations exist.

### R2-11. SEO as standing practice, not ad-hoc — `[x]`
`docs/SEO_PLAYBOOK.md` is now the law: per-page checklist (title, meta desc,
canonical, one unique h1, parsing JSON-LD, sitemap, no orphans, img alt,
breadcrumbs, robots, llms.txt, mobile), hard rules (`| tojson` for all JSON-LD
values; shared partials carry their own CSS), keyword-intent → page map, and a
runnable re-audit script. The first full audit already paid off — fixed: broken
ItemList JSON-LD on all 10 category pages (Python ternary pasted into markup),
missing h1 on `/menu` ("Today's menu") and `/bio` (div → h1). Verified green
across 21 pages: unique titles/descs/h1s, all JSON-LD parses, all imgs have alt.

### R2-12. Repo restructure — `[ ]`
Done so far: junk removal + `docs/` home for agent/misc notes. Deeper rebuild
(defer; low ROI now): consolidate `app/` subpackages (`delivery/`, `whatsapp/`,
`sms/`, `petpooja/`) docs → `docs/`, split `main.py` (>1k lines) into routers.

### R2-13. Branded dish-photo placeholders — `[ ]`
Dishes without photos show an empty green box (category pages now sort
photo-items first, which hides the problem but doesn't solve it). Plan:
- **Design (one sample, Mom approves):** 1080×1080, cream background `#FBF8F2`,
  Tulsi leaf logo top, dish name in Bricolage Grotesque, "100% pure veg ·
  Tulsi Foods, Mylapore" footer line, thin green `#0E7A45` border — same visual
  language as the North Indian Thali poster (green + cream + labelled).
- **Generate, don't photoshoot:** `scripts/make_placeholder.py` (PIL, fonts
  already in repo via Google Fonts links — vendor the .ttf locally) renders one
  `.jpg` per imageless item id into `app/static/img/dishes/`; real photos always
  win (loader prefers existing files, never overwrites).
- **Rollout:** run once for all photo-less ids, commit the files; templates need
  zero changes (they already check `pid in dish_photos`). Alt text stays the
  same shape as real photos.
- **Keep honest:** placeholder is a branded card, never a fake food photo —
  no stock imagery pretending to be the dish.

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

## 3. "Order on WhatsApp" → "Order Now" (stop sending users to a dead chat) — `[x]`

Current problem: CTAs say "Order direct on WhatsApp" and the checkout nudge sends
people to `wa.me/919940062840`, but WhatsApp answers are unreliable while Meta
verification/`WHATSAPP_ACTIVE` are off — a user lands on a chat that may not get a
timely reply. Today the site already has a **real** on-site order flow, so the
WhatsApp CTAs are misleading.

Fix: reposition WhatsApp as optional "talk to us" support, and make the on-site
flow the primary ordering path.

- **[x]** Changed base/meta + landing/menu/bio/category copy from "Order on
  WhatsApp" → "Order online" / "Order online for delivery or pickup".
  (`index.html` skipped — it's dead/unrouted, `/` is served by
  `landing_page()`; candidate for deletion, see R2-12.)
- **[x]** `landing.html` / `category.html` / `bio.html`: primary CTAs now
  point to `/menu` (on-site cart), not `wa.me`. `menu.html`'s cart bar
  already had this right (Checkout → primary, "or continue on WhatsApp"
  secondary).
- **[x]** WhatsApp demoted to a labelled support/fallback link ("Message us
  on WhatsApp") everywhere except `bio.html`'s DIRECT10 section, which is a
  deliberate WhatsApp-only promo mechanic, not stale copy — see Archived
  below for why that's getting replaced anyway.
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

- **Petpooja relay — CLOSED (2026-09-19).** Root cause: `PETPOOJA_REST_ID`
  on Railway was the numeric outlet id (`84713`) instead of the mapping
  code (`c5xeqnhd`) — confirmed by Petpooja support. Fixed on Railway and
  verified live: order #33 (test order, placed via the site) appeared
  under Online Orders → Tulsi API tab for the first time ever, went through
  `Accepted`, and rang on Mom's terminal for real — she cancelled it
  because she didn't realize it was a test and it interrupted her live
  workflow. **Operational follow-up**: give her a heads-up before any
  future test order, or use an unmistakable test name (e.g. "TEST ORDER —
  IGNORE" as the customer name, as earlier sandbox tests did) so she can
  tell it apart from a real one at a glance. See
  `docs/PETPOOJA_INTEGRATION.md`.
- **Borzo live dispatch** — needs wallet balance (`non_cash` payment configured,
  token valid; only funding blocks `create-order`).
- **SMS** — Twilio stays trial (skips, 572006); real SMS only worth it post-upgrade
  + DLT sender, and it's more expensive than WhatsApp.
- **WhatsApp mini flow** — once verified, the in-conversation service reply is free,
  making it the long-term channel (see `docs/META_CONTINGENCY_PLAN.md`).

---

## Archived — decided against (kept for context, not for re-doing)

These were real plans at some point. Explicitly not happening now — don't
resurrect without asking first, but don't re-litigate them from scratch
either if they come up in old docs/design files.

- **Telegram Kitchen Console mini-app** (§1 above). Was meant to give Mom a
  native-feeling kitchen interface while Petpooja wasn't live. Petpooja is
  expected to be fully working within days, at which point its own
  POS/terminal replaces this need entirely. No further Telegram work
  planned — the whole §1 section is now historical, not a queue.
- **`design/Tulsi Foods v2.dc.html` mockup's checkout vision** (Aug 22):
  WhatsApp Flows in-chat multi-screen checkout, live-location share inside
  WhatsApp, Razorpay UPI intents, and a WhatsApp-catalog-driven bot
  (interactive list menus, media carousels, text-command stock toggles).
  Superseded by the real on-site web checkout + Petpooja POS integration
  that actually shipped — a fundamentally different (and simpler)
  architecture. The mockup's **web ordering / landing page** sections are
  largely superseded too (current landing page took a different structural
  direction), though a few copy ideas (stat callouts, sold-out-with-return-
  date instead of greying out) are still fair game to revisit deliberately,
  not because the old mockup says so.
- **DIRECT10 WhatsApp-only discount code** (`bio.html`). Being replaced by
  real discount infrastructure — UTM-tagged QR codes that deep-link into
  the web-app and auto-apply a discount, once-per-device. See Round 3 →
  Growth / marketing infra above.
