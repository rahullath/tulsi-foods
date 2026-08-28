# Tulsi Foods — ROADMAP & Session Log

Saved 2026-08-14. Status snapshot + forward plan + exploratory notes.

---

## A. Status snapshot

**Goal:** Move Tulsi Foods (Mylapore, pure-veg, woman-owned) off Swiggy/Zomato (~27–32% take) to direct ordering — WhatsApp bot + mobile web app + admin, one FastAPI backend.

**Done & green:**
- Bot stack: webhooks (verify + text/interactive parsing + `smb_message_echoes` human takeover), conversation state machine (menu→cart→checkout→status→reorder), dry-run→real sends, SQLite sessions. **Smoke suite 43/43 PASS**.
- Human takeover: chat flagged `human` when mom replies from Business app; admin toggles Bot/Human; admin conversation list.
- Delivery logic: `delivery_fee` (quote, honors free≥700) vs `delivery_quote` (enforces zone min A₹250/B₹300/C₹350).
- **Shiprocket Quick integration (code complete, account not ready):** full hyperlocal delivery package (`app/delivery/`). Auth works, standard couriers available (Blue Dart ₹258). Pincode-based delivery check, address memory for repeat customers, "Food Ready" dispatch button on admin, WhatsApp tracking notifications. Waiting on mom to: (1) add pickup address in Shiprocket panel, (2) enable Quick, (3) note channel ID.
- Live: `api.tulsifoods.app` (Railway, always-on, volume), CNAME live, webhook **active** (object `whatsapp_business_account`, field `messages`, v26.0, verified). Config bumped to `v26.0` and pushed.
- GitHub public: `rahullath/tulsi-foods`. `.env` (gitignored) holds: system-user token, 2nd system-user token (same app/user), `WHATSAPP_PHONE_ID=111402012015862`, `WHATSAPP_APP_ID`, `WHATSAPP_APP_SECRET` (HMAC now enforced), verify token `tulsi_verify`, `SHIPROCKET_API_EMAIL`, `SHIPROCKET_API_PASSWORD`.

**ID map:**
- `714196232763226` = business portfolio "tulsi.foods_chennai"
- `103395849491739` = **production WABA** "kavita lath" (INR, Asia/Kolkata)
- `111402012015862` = production number **+91 99400 62840**, `NOT_VERIFIED`
- `1364864879187318` = old test WABA; `1315948268263578` = dead test number (+1 555) — **recycled; ignore**. All the "100/33" and "Account not registered" errors trace to it.
- Dashboard banner "problem registering +1 555-673-0217" = cosmetic glitch (stale test number); real subscription is active.

**Only gate to go-live:** business verification **in review** (VISA payment method already on file). When Meta confirms → register number with OTP on mom's phone → `code_verification_status` flips → set Railway vars (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID=111402012015862`, `WHATSAPP_APP_ID`, `WHATSAPP_APP_SECRET`) → real sends work, no code changes.

---

## B. Forward plan / thoughts

### 1. WhatsApp message costs — the "1,000 free" worry (partly outdated)
- **Service conversations (customer-initiated) have been FREE and UNLIMITED since Nov 1, 2024** — the old "1,000 free service conversations/month" cap was removed.
- Since Jul 1, 2025 Meta bills **per delivered template message** (conversation pricing deprecated). India rates (Jan 2026): marketing ~₹0.86/message, utility ~₹0.115, authentication ~₹0.115, **service = free**. India billing now in INR.

**Escape technique (cheap legit):**
- Keep everything **customer-initiated + replied within the 24h window** → all free. The bot already works like this (every inbound message opens a fresh free window). ~20–100 chats/day → ₹0.
- Never send templates outside a window (that's what costs money). Order status stays inside the conversation.
- Direct Cloud API (own app + system user) → **no BSP markup** — the real cost escape vs ₹1,500–12,000/mo BSP routes.
- ⚠️ One source claims service messages become billable from **Oct 1, 2026** — unverified; re-check Meta's official pricing page before launch.

### 2. facebook/openapi exploration note
Repo `facebook/openapi` (MIT) has one spec: `business-messaging-api_v23.0.yaml` (WhatsApp Business Messaging, pinned to **v23.0**; we're on v26.0). Could generate a typed Python client / validators via openapi-generator. **Low priority** — our API surface is tiny. Only revisit if we add media uploads + templates. Backburner.

### 3. Meta Developer Tools MCP → feed to me
Endpoint `https://mcp.facebook.com/devtools` (OAuth, 10 `devtools_*` tools). Lets me self-serve: verification status (`devtools_app_review`), list/test webhooks (`devtools_webhook_list/_manage/_test`), API usage/deprecations (`devtools_api_usage`), docs. Useful **while user is abroad**. Plan: add to `opencode.json` (project MCP config); one-time browser OAuth by user.

### 4. Landing page: Wix AI vs Claude design — **done 2026-08-22**
Decided against Wix (domain-connect paywall, lock-in) — restyled the existing `/` page in place instead of a separate marketing page, so the ordering flow (menu→cart→checkout) stays a single page. Shipped:
- Hero band (green gradient, `Fraunces`/`Inter` via Google Fonts) with **pure-veg mark** + **woman-owned** badges, **"Order on WhatsApp" CTA** (`wa.me/919940062840?text=Hi Tulsi, I'd like today's menu`), and a "see today's menu" anchor into the existing menu.
- 3-image collage placeholder row (`/static/img/hero-1.jpg`, `-2.jpg`, `-3.jpg`) — gracefully falls back to a gradient card via `onerror` when files don't exist yet, so real photos (§5) can drop in later with **no code changes**.
- Trust strip (fresh same-day, delivery zone, no platform markup) + a 3-step "how it works" block before the footer.
- Skipped testimonials — no real customer quotes exist yet; don't fabricate them. Add once mom has a few to share.
- Verified: 43/43 smoke suite still green, admin page (`.topbar`) untouched, screenshots checked at mobile (390px) and desktop (1280px).

**Still open:** drop real photos into `app/static/img/` as `hero-1.jpg`/`hero-2.jpg`/`hero-3.jpg` (see §5); Tailwind CDN was skipped in favor of the existing hand-written `style.css` (small enough, avoids a render-blocking CDN dependency).

### 5. Food images plan
- **Recommended:** real phone photos of ~8–12 hero dishes (thalis, paratha, dal, chai) — mom shoots during service (1-page photo checklist: daylight, plain plate, top-down, no clutter). Authentic, free, right for a mom-run kitchen; best for trust/conversion.
- **Alternative/supplement:** AI-generated food images (consistent style) for decorative/lifestyle shots. Caveat: can read as "fake".
- **Stock:** last resort.
- Same images feed WhatsApp catalog later (optional garnish, not required).

### 6. Min-order + no-dead-ends (so nobody gets stuck while user abroad)
Current hard block (zone min ₹250/300/350) can strand a customer. Proposal — **soft minimum, three escape paths always available:**
1. **Top-up suggestion:** cart below min → "₹X short of ₹250 — add one of these: [2–3 quick suggestions]" (keeps cart).
2. **Order anyway:** "ORDER ANYWAY (₹30 fee applies)" path so small orders still go through.
3. **Human handoff everywhere:** dead-end/unrecognized input/"CALL/HUMAN/MOM/HELP" → flag chat human → **mom gets it on WhatsApp Business app (Coexistence)** + shows in admin. Bot never ends a thread silently; every turn ends in a question or a path.

Additional resilience for the abroad period:
- Order confirmation stays the single source of truth (bot + admin record it); admin shows customer number as one-tap `wa.me`/`tel:` links.
- Fail-safe bot reply ("I didn't catch that — try MENU, or message us and mom will reply") for all unexpected input.

---

## C. Go-live checklist
1. Meta confirms business verification.
2. Register number `+91 99400 62840` with OTP on mom's phone → `code_verification_status` = VERIFIED.
3. Update Railway vars: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID=111402012015862`, `WHATSAPP_APP_ID`, `WHATSAPP_APP_SECRET`.
4. Real send test to a personal number; full loop (message → webhook → bot reply).
5. Confirm Coexistence / BSP status (see questions) — decides whether mom keeps Business app on same number or we build admin reply box.

### Shiprocket delivery go-live
6. Mom adds pickup address in Shiprocket panel: 34, Murrays Gate Road, Alwarpet, Chennai 600018.
7. Enable Shiprocket Quick (sidebar → Quick, or quick.shiprocket.in).
8. Add wallet balance (prepaid, already done).
9. Note channel ID from Sales Channels (needed for order-based tracking).
10. Test: create order → dispatch → verify rider assigned → track via WhatsApp.

---

## D. Shiprocket Quick integration details

### Architecture
- `app/delivery/shiprocket.py` — full API client: auth (email+password → JWT, cached in SQLite `shiprocket_tokens`), serviceability check, order create, AWB assign, pickup schedule, dispatch flow, tracking (AWB-based + order-based).
- Pickup address: 34, Murrays Gate Road, Alwarpet, Chennai 600018 (pincode 600018).
- Dispatch is manual: mom clicks "Food Ready" on admin → Shiprocket creates order → assigns courier → schedules pickup → WhatsApp notification sent to customer.
- Address memory: repeat customers get asked "Deliver to [saved address]? YES or new address" — stored in `customers` table.
- Tracking: WhatsApp push on dispatch + delivery (automatic via `_send_dispatch_whatsapp()`).
- Payment: COD + UPI. COD collected by Shiprocket rider.

### API endpoints used
- `POST /v1/external/auth/login` — get JWT token
- `GET /v1/external/courier/serviceability/` — check pincode serviceability (only_local=1 for hyperlocal)
- `POST /v1/external/orders/create/adhoc` — create order
- `POST /v1/external/courier/assign/awb/{id}` — assign AWB
- `POST /v1/external/courier/generate/pickup` — schedule pickup
- `GET /v1/external/courier/track/awb/{awb}` — AWB-based tracking
- `GET /v1/external/courier/track?order_id=X` — order-based tracking (richer response)
- `GET /v1/external/settings/company/pickup` — check pickup addresses

### Account status
- Auth works: `kavitalath14@gmail.com` → token generated.
- Standard couriers: Blue Dart Air ₹258 (Chennai→Chennai).
- No hyperlocal couriers yet (Quick not enabled).
- No pickup addresses (mom needs to add).
- Channel ID: 11901391.

## E. Open questions
1. When doing "login using whatsapp business", did any **BSP/partner name** appear (Wati, Yellow.ai, Interakt, etc.)? If yes, may be on their platform instead of direct Cloud API — affects cost.
2. Min-order: soft minimum + order-anyway + human handoff, or keep the block?
3. Images: real photos (mom shoots) vs AI-generated vs both?

---

## E. Handoff note — 2026-08-22 session (for next local session)

**Context:** this session ran in an isolated cloud container with only a fresh clone of the GitHub repo — no access to the user's local machine. User has a local folder `dev/tulsi-foods` with a `media` subfolder containing **lots of photos + menu files** (mixed quality, "tonnes of useless crap" per user — needs strong filtering), which only a **local** Claude Code session can see. Continue there.

**Done this session:**
- Restyled `/` (home/ordering page) per §B.4 landing-page strategy — hero band, pure-veg + woman-owned badges, "Order on WhatsApp" CTA (`wa.me/919940062840`), 3-image collage placeholders, trust strip, 3-step "how it works". Full details + rationale already logged in §B.4 above. Commit: `e7a63cd` on branch `claude/last-commit-date-ka4ete` (pushed, no PR opened yet — user hasn't asked for one).
- Verified: 43/43 smoke suite green, admin page untouched, screenshots checked at 390px/1280px.

**Next, in the local session:**
1. **Photos** — go through `dev/tulsi-foods/media`, pick ~3 best hero-quality shots (daylight, plain plate, top-down, no clutter — matches the photo checklist already in §B.5), crop/compress to reasonable web size (webp/jpg, square-ish aspect), save as `app/static/img/hero-1.jpg`, `hero-2.jpg`, `hero-3.jpg`. The hero markup in `app/templates/index.html` already points at those exact filenames and falls back to a gradient placeholder via `onerror` if a file is missing — dropping the files in is enough, no HTML/CSS changes needed. If there are good shots of specific dishes, consider also wiring per-item thumbnails into the menu list later (not scoped yet).
2. Check `media` for anything else worth surfacing (e.g. an existing paper/PDF menu that reveals dishes or prices missing from `app/menu` or `data/`).
3. **Testimonials** (§B.4 — skipped this session, don't fabricate quotes): user is going to scrape Zomato/Swiggy/Google reviews + collect physical/photo reviews and hand over a real list **later**. When that list arrives: add a "What people say" section to the hero/landing area with a handful of real short quotes (name + platform, no fabricated star ratings beyond what the source shows).

---

## F. Handoff note — 2026-08-27 session (for next session)

Big session — v3 site redesign, a batch of ordering-flow follow-ups, SEO work, a curated-reviews system, Google Maps checkout, and packing/GST. All pushed to `master`; commits `88f5c08` through `b1cdc9c` cover the follow-up-features and SEO/reviews/GST work specifically (`git log --oneline` for the full list). Summarizing what's **still open** rather than re-describing everything already shipped and verified.

### Needs your action (not code — real-world steps)

1. **Google Maps/Places in production** — was mid-troubleshoot when this session ended. Root cause found: 7 different API keys exist in the Google Cloud console (all created the same day), and there's no way to tell which value actually made it into Railway's env vars. Agreed fix: use the key named **"API key 3"** (no restrictions, works for both purposes) for both `GOOGLE_MAP_API_KEY` and `GOOGLE_PLACES_API_KEY` in Railway, with `GOOGLE_PLACE_ID=ChIJUTRGijNmUjoRsJrKQ5jJBM8`. **Confirm this is actually done and working** — last verified state was still broken. Once confirmed stable, delete the other 6 unused keys in Cloud Console to stop this recurring.
2. **Borzo is still in test**, per the user directly — don't trust `.env`'s production-looking URL/token as a signal either way, ask directly before assuming.
3. **GST rate/registration** — the 5% figure and the "restaurant is GST-registered" conclusion are inferred from Swiggy CSV patterns (see commit `b1cdc9c` message for the exact evidence), not confirmed with a CA. Worth an actual 10-minute check before this matters for real money. Also worth checking whether Kavita's dine-in bills already itemize GST — if so, that's one more reason the itemized checkout approach is right.
4. **Packing fee amounts** (₹20 flat / ₹40 for orders ≥ ₹1000, in `app/config.py`) are starting estimates, not measured numbers — retune based on actual container/packaging cost.
5. **"Offset GST via commission savings" idea** — user's own idea, explicitly deferred, not built. `orders.gst_for()` is kept as a single isolated function specifically so this is a small follow-up later, not a rewrite.
6. **Admin Reviews tab is empty of real content** — the system (`/admin` → Reviews) works and is verified, but someone needs to actually type in real quotes (physical stickers, WhatsApp praise, Swiggy/Zomato reviews) and toggle them featured. Swiggy/Zomato platform numbers are already filled in with real figures; Google's rating auto-refreshes once the Maps API key issue above is resolved.
7. **GA4 conversion events** — base `gtag.js` is live site-wide, but nothing fires custom events yet (`click_to_call`, `click_to_whatsapp`, `order_form_submit`) — explicitly put on hold by the user ("we will do ga4, keep in mind"), not forgotten.
8. **PageSpeed/Lighthouse check** — never actually run against the live site this session. Worth doing once before treating the technical SEO work as fully closed.
9. **Google Business Profile** — manual work only (photos, attributes, weekly Posts, replying to reviews), can't be touched from code. Per the SEO research this session, still the single highest-leverage item left.

### Cashfree — researched, not built

`pay/cashfree-agent-skills.md` (untracked, still just this one file) is a doc about installing Cashfree's *AI-assistant reference skills* via `npx @cashfreepayments/agent-skills` — not an actual integration, and running that installer wasn't done this session (would write a `cashfree-skills/` tree + `CLAUDE.md` manifest at repo root — fine to do later, just noting it hasn't happened). Pulled the real Cashfree docs directly instead:

- Auth: `x-client-id` / `x-client-secret` / `x-api-version` headers; sandbox at `sandbox.cashfree.com/pg/`, production at `api.cashfree.com/pg/`. Separate credential pairs per product (Payments vs Payouts) and per environment.
- `POST /pg/orders` (Create Order) takes `order_amount`, `order_currency`, `customer_details` (`customer_id`, `customer_phone`), optional `order_id`; returns `payment_session_id`.
- For a server-rendered site like this one (not a JS SPA), **Hosted Checkout** is the right flow — redirect the browser using the `payment_session_id`, not the JS Drop-in/Elements SDK.
- Payment confirmation needs a **webhook** (same signature-verification pattern already built for Borzo in `app/webhooks.py`) — a return-URL redirect alone isn't trustworthy for marking an order paid.
- Couldn't load the hosted-checkout integration page or the webhook signature-verification page this pass (both 404'd — Cashfree's docs site structure seems to have shifted under the URLs their own `llms.txt` index pointed at). Re-fetch `https://www.cashfree.com/docs/llms.txt` for current paths once mom's verification actually completes and real sandbox keys exist — better to build against a live sandbox than docs pages that won't load anyway.
- Mom's "in verification stage" almost certainly means Cashfree's own KYC on their dashboard, not anything in this repo.

### Petpooja Online Ordering API — decision made, waiting on credentials

Petpooja (or a partner) emailed offering order-relay APIs into Petpooja — the POS system this business already appears to use (inferred from the "Container Charge" line and report structure in the daywise/itemwise CSVs analyzed this session). Quote: **₹3,000/outlet/year, exclusive of GST**. Contact is Malvi Vaghela. The apiary.io docs URL 502'd for a while but the real spec (`temp/petpooja-api.txt`, not committed) was reviewed this session — **decision: proceed**, subject to getting real credentials. Confirmed from the spec:

- **It's a two-way integration.** `Save Order` (POST to a Petpooja-hosted endpoint) pushes a website order into her PoS as a new order; `Order Callback` (a webhook *we* host, its URL passed in every Save Order call) is how Petpooja tells us the order was accepted/dispatched/food-ready/delivered/cancelled — maps cleanly onto `app/db.update_order_status()` and the existing `_send_status_whatsapp()` in `app/main.py`.
- **Confirmed the exact thing the user asked about**: per the spec (line 193), a pushed order lands in Petpooja in "Pending State until the restaurant partner respond (Accept/Reject)" — the *same* queue Swiggy/Zomato orders already sit in. It only prints once she accepts, using the exact accept/reject motion she already does today. Zero new behavior required from her.
- **Bonus not in the original pitch**: this makes kitchen fulfillment of website orders independent of WhatsApp/Meta entirely. Right now that path runs through this app's own admin dashboard and (for status updates) WhatsApp, which is stuck behind Meta's pending Business verification (see item below). Routing through Petpooja instead means a website order gets made and delivered the same way regardless of whether Meta ever finishes reviewing the app.
- Also available, phase-2 candidates once the core loop works: `Update Item/addon In/Out of Stock` (Petpooja → us, so marking something sold out in her POS auto-syncs to the website instead of needing `db.set_availability()` done twice), `Push Menu` (could eventually replace hand-maintained `data/menu.json`), a `Rider Information` webhook (us → Petpooja, forwarding Borzo delivery events), and store open/closed sync.
- **Blocker**: `app_key`/`app_secret`/`access_token`/`restID` are all issued by Petpooja after registering — there's a staging environment (`developerapi.petpooja.com`) but no self-serve signup, so nothing can be built-and-tested until Malvi/Petpooja provides staging credentials. Next real-world step is asking her for that, not writing code against a schema with no live example to check field-nesting against.
- Also flagged in the spec: **Apiary (the docs host) is being retired Oct 31, 2026** — get docs from `developerapi.petpooja.com` going forward rather than relying on the apiary.io link.

### Open from earlier sessions, still unresolved
- WhatsApp Business verification status — last known: still pending Meta review.
- §E "Open questions" above (BSP/partner name check, min-order UX decision) — never confirmed answered in any later session note; worth a fresh look rather than assuming still relevant.
