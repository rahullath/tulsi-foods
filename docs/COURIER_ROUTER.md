# Courier Router — scoped open-source piece (not the whole platform)

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
