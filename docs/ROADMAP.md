# Tulsi Foods — ROADMAP & Session Log

Saved 2026-08-14. Status snapshot + forward plan + exploratory notes.

---

## A. Status snapshot

**Goal:** Move Tulsi Foods (Mylapore, pure-veg, woman-owned) off Swiggy/Zomato (~27–32% take) to direct ordering — WhatsApp bot + mobile web app + admin, one FastAPI backend.

**Done & green:**
- Bot stack: webhooks (verify + text/interactive parsing + `smb_message_echoes` human takeover), conversation state machine (menu→cart→checkout→status→reorder), dry-run→real sends, SQLite sessions. **Smoke suite 43/43 PASS**.
- Human takeover: chat flagged `human` when mom replies from Business app; admin toggles Bot/Human; admin conversation list.
- Delivery logic: `delivery_fee` (quote, honors free≥700) vs `delivery_quote` (enforces zone min A₹250/B₹300/C₹350).
- Live: `api.tulsifoods.app` (Railway, always-on, volume), CNAME live, webhook **active** (object `whatsapp_business_account`, field `messages`, v26.0, verified). Config bumped to `v26.0` and pushed.
- GitHub public: `rahullath/tulsi-foods`. `.env` (gitignored) holds: system-user token, 2nd system-user token (same app/user), `WHATSAPP_PHONE_ID=111402012015862`, `WHATSAPP_APP_ID`, `WHATSAPP_APP_SECRET` (HMAC now enforced), verify token `tulsi_verify`.

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

### 4. Landing page: Wix AI vs Claude design
Recommend **Claude/AI-generated static single-page site** served by FastAPI at `/` (replaces current basic home) — not Wix (domain-connect paywall, lock-in; domain on name.com can point at Railway). Structure: hero + **"Order on WhatsApp" CTA** (`wa.me/91…?text=Hi Tulsi, I'd like today's menu`), today's menu teaser (live from `/api/menu`), how-it-works, delivery zones, pure-veg + woman-owned badges, testimonials, footer + privacy link. Mobile-first, Tailwind CDN, webp images. Wix AI only if insisted (adds monthly cost + redirect).

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

---

## D. Open questions
1. When doing "login using whatsapp business", did any **BSP/partner name** appear (Wati, Yellow.ai, Interakt, etc.)? If yes, may be on their platform instead of direct Cloud API — affects cost.
2. Min-order: soft minimum + order-anyway + human handoff, or keep the block?
3. Images: real photos (mom shoots) vs AI-generated vs both?
