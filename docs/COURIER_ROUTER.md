# Courier Router — scoped open-source piece (not the whole platform)

> **Decision, Oct 2026: Porter only.** Borzo dropped (riders unreliable in our
> radius), Shiprocket unused. Uber Direct checked: in India it is an ONDC-only
> logistics provider, live in Bengaluru since Dec 2025, no merchant API and no
> Chennai service, so not an option yet. Browser automation of porter.in
> (Playwright/Puppeteer) rejected: OTP login, breaks on UI changes, likely
> against Porter's terms, and Porter has a real API we can get instead.
>
> **Live flow** (`app/delivery/porter.py`): POS "Food Ready" → Telegram gets a
> paste-ready Porter booking card → Mom books in the Porter app → admin
> panel "Book" sheet → paste tracking link (+ rider name/phone) → customer gets
> it on WhatsApp/SMS and /track. Checkout charges the zone-table fee
> (`estimate.USE_BORZO_QUOTES = False`).
>
> **Next:** get Porter API access (porter.in/api-integrations → enterprise
> team; the self-serve sign-up was geo-restricted). Then implement
> `porter.quote()`/`porter.book()` and set `PORTER_API_KEY`;
> `orders.dispatch_rider()` already switches to the API path on its own.


Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## 1. Why this, why scoped this way

Borzo and Shiprocket don't service Chennai fast enough for a single-kitchen
restaurant's delivery radius. Rapido would be faster but has **no legitimate
public API** — only unofficial scraped wrappers, not something to build
production delivery on.

The instinct was "send to every courier, keep whoever accepts first, cancel
the rest." That's the wrong model: `create-order` isn't a bid, it's a real
commitment — it dispatches an actual human rider. Racing real bookings across
4 vendors for one order means riders converging on the kitchen, cancellation
fees from every loser once a rider is assigned, and each vendor's
abuse/fraud detection flagging the account for high cancel rates.

**This is explicitly not an attempt to build "an alternative to Swiggy/
Zomato."** That space (ordering + catalog + payments + ONDC compliance) is
already crowded with Seller Network Partners (GrowthFalcons, uEngage,
Magicpin, Waayu, NStore, Nearshopz) and is adoption-hostile for non-technical
owners who can't self-host a backend. The actual gap is narrower: nobody
offers a **free, self-hostable multi-courier delivery router**. Every
existing option (ClickPost, Shiprocket Quick, Pidge) is paid SaaS — the same
subscription model this is trying to avoid. If it can't run without
extracting money from small businesses, it should be open source instead of
a product.

---

## 2. Architecture — quote first, book once

Confirmed pattern from how these APIs actually work (Borzo's
`POST /calculate-order` returns price + validates params *before* you
create the real order — this is the model, not an outlier):

1. **Fan out a quote call** (not a booking call) to every configured courier
   in parallel (`asyncio.gather`). Lightweight, no real rider dispatched.
2. **Filter to serviceable** couriers for the pincode/radius.
3. **Pick a winner** by policy — cheapest, fastest ETA, or first-serviceable.
   This is where "based on cheaper amount" logic lives — at the quote stage,
   never the booking stage.
4. **Call `create-order`/book only on the winner.**
5. **Fallback, not racing**: if the winner fails to get a rider assigned
   within a few minutes, book the next-cheapest from the quotes already
   fetched. Sequential waterfall, never simultaneous live bookings.

Each courier gets the same two-function interface, mirroring the shape of
the existing `app/delivery/borzo.py`:

- `quote(order) -> {price, eta, serviceable}`
- `book(order) -> {tracking_id, ...}`

A thin `app/delivery/router.py` does the fan-out + policy + book + fallback.
No rewrite of what exists — new courier modules sit alongside Borzo's.

- **[ ]** Define the shared `quote()`/`book()` interface as a small ABC or
  Protocol so new couriers are drop-in.
- **[ ]** `router.py`: parallel quote fan-out, policy-based pick, book,
  timeout-based fallback to next-cheapest.
- **[ ]** Don't fan out to *every* vendor on *every* order indefinitely —
  overhead per order for no benefit once win-rates are known. Run broad for
  a couple weeks, then trim to 2 real candidates + one fallback.

---

## 3. Vetted couriers (status as of 2026-08-30)

| Courier | API status | Notes |
|---|---|---|
| **Borzo** | Live in production for Tulsi Foods | `calculate-order` quote endpoint confirmed; keep as baseline/fallback |
| **Rapido** | No legitimate API | Ruled out — unofficial wrappers only |
| **Porter** | Real API (webhooks + live tracking), covers Chennai | Georestricted for this account currently — retry later |
| **Shadowfax** | Real API (Unified Forward Integration), used by Zomato in production | Have test + prod tokens — **rotate the prod one**, it was pasted in plaintext in chat and should be treated as exposed |
| **Blitznow, Qwqer, Adloggs** | Contacted / access pending | Legitimacy of a real merchant API not yet confirmed — verify before integration work, same trap as Rapido |

---

## 4. Scope decision

- **v0.1 = the router only.** Plugs into whatever ordering system already
  exists (this FastAPI backend, or someone else's) via the same interface —
  not a replacement for the ordering site, Petpooja, or ONDC listing.
- Explicitly **not** building the full "alternative to Swiggy/Zomato"
  platform as v1. Revisit only if the router itself gets real adoption
  outside Tulsi Foods.
- License: open source, no paid tier gating core routing — the whole point
  is not extracting from small operators the way SaaS aggregators do.

## Backlog / parked

- Extract into its own repo once proven stable on live Tulsi Foods orders
  for a few weeks.
- Selection policy: hardcode cheapest-first for v0.1, make it configurable
  (cheapest vs fastest ETA) later if a second real user shows up.
- Evaluate Waayu / NStore / Nearshopz as ONDC-side SNPs — separate track
  from this router, tracked in the ONDC research above (not yet a doc).

## POS-driven Porter loop (Oct 2026) — no admin panel needed

1. **POS Accept** (Petpooja callback status 1-3, first time) → Mom gets the
   Porter booking card on WhatsApp (+ Telegram if configured).
2. **POS Food Ready** → reminder, only if no rider is recorded yet.
3. Mom books in the Porter app, taps Share on the trip and sends the link
   to the business WhatsApp number (add `#<order>` if 2+ orders are waiting).
4. The bot attaches it to the order → out_for_delivery → customer gets the
   tracking link → Mom gets "✅ Order #N is out for delivery".

Code: `app/kitchen_alerts.py`, `app/webhooks.py` (`_maybe_auto_dispatch`,
inbound admin messages). Admin panel "Book" still works as a backup.

### Railway variables to set
- `WHATSAPP_ACTIVE=1`
- `ADMIN_PHONE` = Mom's personal WhatsApp in wa_id form, e.g. `919XXXXXXXXX`.
  It must NOT be the business number itself (a number can't message itself).
- `KITCHEN_WA_TEMPLATE` = name of an approved UTILITY template whose body is
  just `Kitchen alert: {{1}}` (language `en`). Without it, alerts only reach
  Mom within 24 h of her last message to the business number.
