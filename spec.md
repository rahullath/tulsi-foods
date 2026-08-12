# Tulsi Foods — Direct Ordering System (WhatsApp + Web)

A practical spec for replacing Swiggy/Zomato with a direct ordering system for **Tulsi Foods, Mylapore, Chennai** — a woman-owned vegetarian restaurant (thalis, chaats, parathas, Italian, desserts, beverages) running on **Petpooja POS**.

This v2 spec is grounded in the restaurant's actual sales data (May–Aug 2026 exports). Where v1 made generic assumptions, this version uses real menu, order sizes, delivery distances, and channel mix.

---

## 0) Business context (why we're building this)

- **Channel mix (May–Aug 2026):** online = ~35% of revenue (Swiggy ₹4.1L, Zomato ₹1.5L, Toing ₹1.8K); **direct = ~65% (₹10.4L)**. The direct base already exists.
- **What the aggregator keeps:** ~27% of the customer's bill (20% fee + 18% GST on the fee + collection charges + ads). July example: customer paid ₹1.47L, restaurant netted ₹99.6K.
- **Per-order reality:** platform order nets ~67.7% of the bill. A direct order at 15% below app prices nets more than a platform order *and* the customer pays less.
- **Kitchen load:** 192 orders in the 11–14h lunch window and 162 in 18–20h on platforms. Smoothing this is a core goal.
- **Delivery footprint:** median last-mile 2.4 km; 67% of orders ≤3 km, 91% ≤5 km, 97% ≤7 km.

Goal: shift a large share of the 35% online revenue to direct channels over 3 months, without dropping sales, without adding staff burden, and without blocking orders at any time.

---

## 1) Core principles (non-negotiable)

- **Customers never need a new app or account.** Channels: WhatsApp (primary for chat ordering) + a **mobile-first web page** (equally important — the web is not an afterthought).
- **Orders flow straight into Petpooja POS** like dine-in/takeaway. No double entry; one kitchen queue.
- **The restaurant owns all customer data.** Phone numbers, order history, preferences. No aggregator data locks.
- **Availability is first-class.** The kitchen can't make every menu item every day. Unavailable items are hidden or clearly flagged everywhere, *before* the customer starts ordering — never discovered mid-flow.
- **Orders are never blocked.** Pre-ordering is *recommended and incentivised*, never required. Customers can always order "now".
- **Cheap to run, hard to break.** Minimal dependencies; manual WhatsApp fallback when anything goes down.
- **Built for one person to build and a small team to operate.**

---

## 2) High-level architecture

### Components

1. **WhatsApp interface** (WhatsApp Business Cloud API)
   - Menu display (today's menu only)
   - Order capture (cart, qty changes, item codes)
   - Availability-aware item selection with instant alternatives
   - Confirmation, status updates (preparing / out for delivery / delivered)
   - Basic support ("change address", "cancel order", "talk to staff")

2. **Web app** (first-class, mobile-first)
   - Today's menu with live availability
   - Cart + checkout (COD / UPI)
   - Optional handoff: "Continue on WhatsApp" for chat ordering
   - Shareable links for Google Business, Instagram, flyers/QR

3. **Ordering backend**
   - Sessions by phone number (WhatsApp) / session or phone (web)
   - Cart, pricing rules, taxes, delivery fees, zones, time slots, order history
   - APIs: menu, availability, create order, update status, order history

4. **Petpooja POS integration**
   - Menu + prices sync (source of truth for catalog)
   - Push WhatsApp/web orders in as "Delivery"/"Pickup" so kitchen prints the same ticket
   - Status pull if available → WhatsApp notifications
   - Daily availability managed in our admin, pushed to channels

5. **Admin dashboard (phone-friendly)**
   - **"Today's menu" availability screen** (the most-used feature — see §3)
   - Live orders board (New / Preparing / Ready / Out for Delivery / Delivered / Cancelled)
   - Delivery zones, fees, time-slot config
   - Promotions (simple discount rules)
   - Analytics + weekly scorecard (§10)

6. **Delivery logistics** — delivery tool/provider TBD by owner (own riders vs delivery-only partner like Semja). Backend exposes zones, fees, ETAs, rider handoff info regardless of choice.

### Data flow

```
Petpooja ──menu sync──▶ backend ──today's menu──▶ WhatsApp bot + web app
Petpooja ◀─order push── backend ◀──orders── WhatsApp bot / web app
admin (today's menu) ──▶ backend ──availability──▶ WhatsApp + web
backend ──status──▶ WhatsApp (preparing / out / delivered)
```

---

## 3) "Today's menu" — availability, done right (the heart of this system)

**The problem:** the kitchen can't cook all 150+ menu items every day. If a customer picks an unavailable item mid-order, they either restart the whole flow or get a substitution surprise — both make direct ordering feel worse than the aggregators.

**The solution — a daily availability model:**

1. **Default = yesterday.** Every morning the "today's menu" is pre-populated with yesterday's availability. One tap = "repeat today".
2. **One-tap toggles.** A grid of items grouped by category; big toggle per item. Designed for a phone screen and 30 seconds of use. Also supports time-based rules (e.g., chai until 9 PM, no lunch items after 3 PM, snacks from 4 PM).
3. **Push to all channels in seconds.** The toggle instantly updates the WhatsApp menu and the web menu. No caching lag beyond ~30–60s.
4. **Never a mid-flow surprise.**
   - WhatsApp: unavailable items aren't listed (or are shown as "not today"). If a customer requests one, the bot replies immediately: *"Not available today. Try [1-2 alternatives from same category] instead?"* — one tap to swap.
   - Web: unavailable items are hidden or greyed; carts are re-validated before checkout; if an item in the cart becomes unavailable, the checkout screen flags it with one-tap replacements.
5. **Special/prep-days.** A separate quick note field ("closed Wed", "special: [dish] today") shown at the top of both channels.

**Why this matters more than any other feature:** it removes the biggest friction point between "menu exists in POS" and "kitchen can actually cook it today," and it's the single feature that keeps mom in control without adding her work.

---

## 4) Customer experience — WhatsApp

### Onboarding

- Existing customers save the number, send "Hi" or "MENU".
- New customers find the number via Google Business, Instagram, flyers, or the web link.
- Intro message: welcome + today's special + **pre-order hint as a recommendation only**: "Tip: order before 11 AM for lunch to beat the rush." Ordering now is always allowed.

### Menu & ordering

1. Customer sends "MENU" → bot sends today's categories, e.g.:
   - 1 Thalis & Combos
   - 2 Parathas & Breads
   - 3 Chaats & Snacks
   - 4 Soups & Rice
   - 5 Chai & Beverages
   - 6 Desserts
2. Category → item list with codes, short description, price, "popular" tag where true. Unavailable items omitted (or "not today").
3. Selection by code/name: `A1, B3 x2` or guided (`1` → qty → done).
4. Live cart: running total after each add; edit via "remove 2", "change 1 to x3".
5. **Add-on nudge (data-backed):** after the main item is in the cart, suggest high-frequency add-ons — Masala Chai, Gulab Jamun, Masala Papad, Buttermilk. (Chai alone was on ~280 orders in 2 months.)

### Checkout

1. Confirm cart: items, qty, prices, subtotal, delivery fee, total.
2. Capture/confirm: delivery address (saved for repeat customers), time ("Now" or a slot), name.
3. Validate: address in zone? slot acceptable? If "Now" during peak, show honest estimate ("~45 mins at the moment") rather than refusing.
4. Payment: COD (default) or UPI payment link/QR. Pay-at-restaurant for pickup.
5. Final summary → "Reply YES to confirm."
6. Confirmation: order #, prep estimate, expected delivery time.

### Post-order & repeat

- Status updates: Preparing → Out for delivery (rider info if applicable) → Delivered + feedback prompt (1–5).
- "STATUS" any time; "Issue with order #" routes to staff.
- **REORDER** (last order), favourites, and "your usual" — ordering direct should be *easier* than an aggregator app.

---

## 5) Customer experience — web app

As important as WhatsApp. Some customers will never chat to order; they want to tap and pay.

- **Mobile-first single page.** No install, no account required to browse. Phone number captured at checkout (identity for repeat ordering).
- **Today's menu** rendered from live availability. Clear "today" framing; out-of-stock items hidden/greyed.
- **Cart + checkout:** name, phone, address (with zone auto-detection), time slot, COD or UPI link.
- **WhatsApp handoff:** a "Continue on WhatsApp" button that carries the cart into a chat — customers who prefer chat don't re-type.
- **Shareable:** one link for Google Business / Instagram / flyers / WhatsApp status. QR printed on flyers and billing slips.
- **Repeat flow:** optional "remember me" (phone-based) → saved address + REORDER-style one-tap repurchase.
- **Accessibility:** readable font sizes, prices clear, veg marker, filter by category, search.

### Roadmap (not v1)

- **QR self-order at tables** (web app already fits — same code path, "dine-in" order type).
- Loyalty/points — explicitly deferred; not needed to win.

---

## 6) Operations & Petpooja integration

Petpooja is the restaurant's POS (confirmed). Integration goals: no double entry, one kitchen queue, menu and availability stay correct.

1. **Menu sync:** pull categories, items, prices, modifiers, veg flags, availability from Petpooja; cache in backend; periodic sync (5–10 min) + manual trigger.
2. **Order push:** confirmed WhatsApp/web orders → Petpooja as "Delivery"/"Pickup" with items, qty, modifiers, customer name/phone/address, payment method, special instructions. Kitchen ticket prints like a dine-in order.
3. **Status sync (if supported):** map Petpooja status → WhatsApp updates (accepted → confirmed, preparing, ready → out for delivery, completed → delivered).
4. **Availability:** daily availability lives in our admin and pushes to WhatsApp/web. Keep Petpooja as the catalog source of truth; if Petpooja exposes availability, two-way sync where possible.

**First integration task (build order):** verify Petpooja's actual API capabilities (menu fetch, order create, status pull, availability). The rest of the spec is built to tolerate any combination of those.

---

## 7) Delivery

Provider decision (own riders vs Semja-style delivery-only partner) is the owner's call — planned separately. The backend is provider-agnostic.

### Zones (from actual delivery data — 909 delivered orders)

| Zone | Radius | Share of orders | Suggested fee | Suggested min order |
|---|---|---|---|---|
| A (core) | 0–3 km | 67% | ₹30 | ₹250 |
| B | 3–5 km | 24% (cum. 91%) | ₹50 | ₹300 |
| C | 5–7 km | 6% (cum. 97%) | ₹70 | ₹350 |
| D | 7+ km | 3% | pickup only / case-by-case | — |

Median distance is 2.4 km — the core zone is dense and cheap to serve. Fees can undercut Swiggy/Zomato in the core and still beat their take on the restaurant side.

### Time slots & capacity

- "Now" always accepted; during peaks show an honest prep estimate instead of rejecting.
- Scheduled/pre-orders offered and promoted (lunch cutoff 11 AM, dinner cutoff 5 PM) to batch cooking — **recommended, never mandatory**.
- Optional per-slot order caps to protect kitchen; if a slot is full, suggest the next slot (never a dead end).

---

## 8) Payments & reconciliation

- **COD** (default), **UPI payment link/QR** (webhook confirm or manual), **pay-at-restaurant** for pickup. No complex card integrations in v1.
- Admin daily/weekly summaries: orders, COD vs UPI split, revenue, delivery fees, refunds/adjustments; CSV export for accounting.

---

## 9) Retention & offers (no gimmicks)

Real, data-tuned mechanics only:

1. **Direct-order discount (the headline):** ~15% off direct orders vs app prices. Simple, legible, already the marketing plan.
2. **First-order incentive:** e.g., ₹50 off first WhatsApp/web order — conversion lever for flyer leads.
3. **Repeat incentive:** after N orders (e.g., 5), a discount — not free dessert; track by phone number.
4. **Time-based (optional later):** weekday lunch 10% off to fill slow slots.
5. **Referral (lightweight):** "share the link — you both get ₹50 off on next order." Manual tracking is fine initially.

**Order-size reality (July):** median order ₹286, 51% of orders under ₹300, 8% under ₹150. Discounts must be structured so small orders (sub-₹250) aren't the target — that tier is loss-making at platform cost. No dessert-as-bait (not confirmed as desirable).

---

## 10) Analytics & decision support

### Seed from day one

The existing Swiggy/Zomato exports (May–Aug 2026) already give baselines — load them at launch so the very first week compares against real prior numbers, not empty graphs:

- Weekly orders, revenue, AOV per channel
- Top items by revenue/qty (thalis, parathas, chaats, chai)
- Order-value bands and delivery-distance distribution

### Core metrics (dashboard)

- **Orders:** per channel (WhatsApp vs web vs phone), by hour/day.
- **Revenue:** total, AOV, by category, direct-vs-platform split.
- **Customers:** new vs returning, 30-day repeat rate, top 20 customers by revenue (targeted offers; the July export already has phone numbers as a starting list).
- **Menu:** top 10 items, low-converting items, frequently paired items (combo ideas).
- **Delivery:** avg delivery time, late rate, complaints.
- **The weekly scorecard:** one screen — direct orders/revenue/AOV vs same week on Swiggy/Zomato. This is the proof it's working and the trigger for the migration taper.

Keep it simple: a few charts + tables + CSV export.

---

## 11) Migration plan (3 months, actual strategy)

**Month 1 — parallel run + flyers**
- Keep Swiggy/Zomato live.
- Every online order ships with a flyer/insert: direct-order link + WhatsApp number + "15% off direct orders" (first order + ongoing direct discount).
- Put the link on Google Business, Instagram, WhatsApp status, billing slips.
- Track direct-vs-platform weekly.

**Month 2 — price the apps out of the market**
- Raise app prices ~25% (reflects the commission they'd otherwise take).
- Raise/change minimum order on apps (kill the sub-₹250 loss tier).
- Direct pricing stays ~15% below original app prices — now the gap is ~40% between direct and app.

**Month 3 — consolidate**
- Scorecard review: if direct is stable, keep reducing aggregator promos (stop featured/ads spend — that was ~₹6.6K over 4 months for little measurable return).
- Long-term: aggregators become discovery-only; target >60–70% of orders direct.

---

## 12) Reliability & fallbacks

- **WhatsApp API down:** staff handle orders in normal chat; backend "manual entry" pushes them into Petpooja.
- **Server down:** static page with today's menu + WhatsApp number + instructions; staff take orders manually.
- **Petpooja down:** orders logged in backend, synced to Petpooja when it's back; WhatsApp confirmations still sent.
- **Support:** "talk to staff" routes to a human; "issue with order #" logs a ticket; simple resolution (refund / discount on next order / note).

---

## 13) Tech stack (practical, not fancy)

- **Backend:** Python (FastAPI/Flask) or Node (Express/Nest). PostgreSQL (or SQLite to start).
- **WhatsApp:** Meta WhatsApp Cloud API (or provider like Gupshup/Twilio). Sessions keyed by phone.
- **Web app:** mobile-first frontend (React/Vue/Svelte or server-rendered), shareable link.
- **Petpooja:** official API for menu fetch, order create, status.
- **Deploy:** single VPS (Hetzner/DigitalOcean/Linode), Docker, basic monitoring, DB backups.

---

## 14) Roadmap (explicitly deferred)

1. **QR self-order at tables** — the web app already fits; add "dine-in" order type later.
2. **Loyalty/points** — not needed to win; revisit after direct channel is stable.
3. **Own delivery fleet** — only after zone economics are proven.

---

## 15) Data still needed to finalize

- Exact current menu items, prices, categories, modifiers (Petpooja export or screenshot) — for the v1 catalog.
- Delivery tool decision (provider + per-order cost) — finalizes zone fees.
- (Optional) current customer phone list to seed the direct-order outreach.
