# Tulsi Foods — Complete Business Memory for Mom's AI Assistant

> **Purpose:** This document is a memory file to import into a local AI app so the
> AI can help **Mom** (the owner of Tulsi Foods) write professional complaint and
> follow-up emails to **Swiggy, Zomato, and other platforms** that keep deducting
> money from her settlements — often without her consent or a clear invoice.
>
> It contains (A) a complete snapshot of the business as it runs *today* in her
> daily life, (B) a full breakdown of the aggregator fee problem with the actual
> numbers from her own exports, (C) a description of the new direct-ordering app
> (which exists as working infrastructure but is **not yet** part of her daily
> routine), and (D) a complaint-writing playbook with ready-to-adapt email
> templates.
>
> All figures come from the owner's own Swiggy/Zomato exports and reports. Only
> use facts from this document — **never invent order numbers, amounts, or dates.**

---

## 0. How to use this document

1. Import this file into the AI app as a knowledge base / system memory.
2. Mom (or her son) asks for help, e.g.:
   - "Draft an email to Swiggy about a ₹13,539 deduction on 1 Aug I never agreed to."
   - "Write to Zomato asking for an itemised statement of July fees."
   - "Reply to Swiggy's response to my last complaint."
3. The AI should:
   - Reference **Part B** for the exact charge names, amounts, and dates.
   - Reference **Part D** for tone, structure, and escalation rules.
   - Quote only figures that appear in this document or that the user pastes in.
   - Always leave blanks/labels for anything not in this file (e.g. "Order No."
     must be filled from the invoice) instead of making it up.
   - Keep the tone **firm, polite, factual, and specific** — restaurants win
     faster with receipts and row-level references than with emotion.
4. When new bank statements, settlement reports, or responses arrive, add them
   to **Part B** so the memory stays current.

---

## PART A — The business as it runs today (Mom's daily world)

### A.1 Fact sheet (always true)

| Item | Value |
|---|---|
| Restaurant | **Tulsi Foods** (also appears as *Tulasi Foods* / *Thulasi Restaurant*) |
| Type | Pure-vegetarian, home-style North Indian "tiffin + thali" restaurant |
| Location | Mylapore / Alwarpet, Chennai, Tamil Nadu, India |
| Address | 34 Murrays Gate Road, Alwarpet, Chennai 600018 |
| Founded | 2015 (11 years of operation as of September 2026) |
| Owned by | A woman restaurateur ("Mom") + small family team |
| Phone | +91 99406 21800 |
| WhatsApp | +91 99400 62840 (also the storefront texting number) |
| UPI (pay to) | tulsifoods@icici ("Tulsi Foods") |
| Hours | Mon–Sat 9:00 AM – 9:00 PM; Sun 11:00 AM – 9:00 PM |
| Monday special | Opens **14:00** (lunch service starts late Monday) |
| Specialty | Ordered-to-order cooking, no onion/garlic & Jain meals on request |
| POS system | **Petpooja POS** (kitchen print terminal) |
| Shown on | Google Maps, Swiggy, Zomato, JustDial |
| GST | 5% (intra-state restaurant GST) |

### A.2 What is cooked (the menu)

- 141 menu items across **10 groups**:
  1. Thalis & Combos  2. Parathas & Breads  3. Chaats & Snacks  4. Sabzi
  5. Starters  6. Soups & Rice  7. Chai & Beverages  8. Desserts
  9. Italian  10. Specialities (only on **Thursdays**)
- Signature / best-selling items (from real sales data):
  - **North Indian Thali** and **Mini Thali** — the boxes (compartments for
    curd, jeera rice, gulab jamun, veg kofta, dal tadka, phulkas, salad,
    mix veg). The most photo-worthy items on the menu.
  - **Phulka** — highest quantity sold (1,454 pcs in 2 months).
  - **Sabudana Vada (2 pcs)** — top snack item.
  - **Masala Chai** — the #1 add-on (on ~280 orders in 2 months).
  - Frequent partners to a thali order: Masala Chai, Gulab Jamun, Masala
    Papad, Buttermilk.
  - Other popular dishes: Aloo Paratha, Channa Masala, Aloo Tikki,
    Tomato Soup, Gulab Jamun, Regular Pizza (Italian group).
- Most items are available in **half portions** for variety.
- Availability is real and daily — the kitchen cannot cook all 141 items every
  day; Specialities only exist on Thursdays; Monday lunch starts at 14:00.

### A.3 How orders actually arrive TODAY (Mom's real channels)

| Channel | What it is | Share of revenue (May–Aug 2026) |
|---|---|---|
| **Direct** — phone calls, WhatsApp chats, walk-ins, regulars | The pre-existing base | **~65% (≈ ₹10.4 lakh over 4 months)** |
| **Swiggy** | Food delivery aggregator #1 | ~25% (₹4.1 lakh over 4 months) |
| **Zomato** | Food delivery aggregator #2 | ~9% (₹1.5 lakh over 4 months) |
| **Toing by Swiggy** | Swiggy's low-cost channel | negligible (≈ ₹1,800) |

- July 2026 in detail: Swiggy **322 orders / ₹1,44,108**, Zomato **140 orders /
  ₹62,066**, Toing **2 orders / ₹309**.
- The daily rhythm: morning preparation → kitchen accepts incoming orders on
  the **Petpooja POS** print queue (same queue for Swiggy, Zomato, and
  dine-in/takeaway tickets) → food is cooked to order and packed → delivered
  (by platform riders for aggregator orders) → settle up later.
- Peak kitchen load (platforms): about **192 orders** in the lunch window
  (11 AM–2 PM) and **162 orders** in the dinner window (6–9 PM).

### A.4 Delivery profile (from 909 delivered orders)

- Median delivery distance: **2.4 km** (very local neighbourhood).
- 67% of orders ≤3 km; 91% ≤5 km; 97% ≤7 km.
- Small orders dominate: **median order ₹286**; 51% of orders are under ₹300
  and 8% under ₹150.
- Conclusion: this is a dense, local, low-ticket delivery business — which is
  exactly why aggregator percentage fees hurt.

### A.5 The POS and partners

- **Petpooja POS** — the kitchen's order printer/terminal; the one system that
  already unifies Swiggy/Zomato/dine-in. Paid: ₹3,000 per outlet per year.
  Petpooja contacts: Malvi Vaghela (sales), Rohan Sakhrani (API support),
  Shivam Tiwari (associate PM).
- **Borzo** (formerly WeFast) — a courier service whose riders are used for the
  *new app's* direct deliveries (see Part C).
- **Shiprocket Quick** — was previously wired for hyperlocal dispatch; superseded
  by Borzo for the direct app.

---

## PART B — The money problem: aggregator charges taken "without consent"

### B.1 How a Swiggy settlement works (the fee anatomy)

Every Swiggy order in Mom's export (`01_swiggy_orders_fee_annexure.csv`, 938
orders May–Aug 2026) is settled using this logic:

```
Customer payable  = Item total + Packing/Service charges − Customer discount
                    + GST liability
Swiggy's cut      = Platform Service Fee (20% of customer payable)
                  + GST @18% on all Swiggy fees
                  + Collection Charges + Access Charges
                  + Long-Distance / Swiggy One / Pocket Hero / Bolt fees
                  + Merchant Cancellation Charges + Call Center Fees
                  + Delivery fee "sponsored by merchant" (if any)
Net to restaurant = Customer payable − Swiggy's cut − (TCS/TDS)
```

**The hard numbers (938 orders, May 5–Aug 12 2026):**

| Metric | Amount | % of customer spend |
|---|---|---|
| Customer payable (net) | ₹3,93,398.67 | 100% |
| Total Swiggy fees (incl. 18% GST on fees) | ₹1,08,158.20 | **27.5%** |
| — Platform Service Fee (@20%) | ₹78,548.82 | 20.0% |
| — Collection Charges | ₹7,841.40 | 2.0% |
| — Merchant Cancellation Charges | ₹1,998.48 | 0.5% |
| Net the restaurant actually received | ₹2,63,477.92 | **67.0%** |

> So roughly **₹1 out of every ₹3** a Swiggy customer pays goes to Swiggy.
> A separate July example: customers paid **₹1.47 lakh** that month, and the
> restaurant netted only **₹99.6K**.

### B.2 The "adjustments and ads" ledger — the unexplained debits

This is the file Mom needs for complaints (`02_swiggy_adjustments_ads_fees_annexure.csv`).
These are **separate line-item adjustments** Swiggy debits on top of the per-order
fees. Total debits over May 17 – Aug 8 2026:

| Charge label | What it looks like | Debits | Total deducted |
|---|---|---|---|
| **LAST_WEEK_OUTSTANDING_CURRENT** | Repeat claw-backs of "last week's outstanding" money, taken *after* the normal settlement | 9 | **₹77,141.13** |
| **TOP_PICKS_ADS** | Weekly ad "Top Picks" fee, auto-recurring | 11 | ₹4,056.25 (₹368.75/week) |
| **HIGH_PRIORITY** | Sponsored-listing charges | 8 | ₹1,766.65 |
| **HOMEPAGE_BANNER** | Homepage banner ad charges | 3 | ₹824.12 |
| **ADS_OFFERS** | Occasional ad/offer fee | 1 | ₹2.36 |

The **LAST_WEEK_OUTSTANDING_CURRENT** line is the most important one to fight:
Swiggy keeps taking roughly ₹5–13 thousand every 1–2 weeks, labelled only as
"outstanding from last week," with **no per-order invoice attached**. Individual
debits in the file: ₹10,545.66 (May 17–19), ₹6,551.20 (May 24–26), ₹6,423.37
(Jun 7–9), ₹10,895.43 (Jun 14–16), ₹8,089.71 (Jul 5–7), ₹8,318.25 (Jul 12–14),
₹7,373.68 (Jul 19–21), ₹5,404.47 (Jul 26–28), ₹13,539.36 (Aug 1–4).

The **ad charges** (TOP_PICKS_ADS + HIGH_PRIORITY + HOMEPAGE_BANNER +
ADS_OFFERS = ~₹6,650 over 4 months) are the "charged without my consent" cases:
ads typically auto-enrolled and renewed weekly (TOP_PICKS_ADS is a fixed
₹368.75 every single week for weeks on end).

### B.3 Swiggy fee vocabulary (so Mom can name the charge in an email)

- **Platform Service Fee (G):** Swiggy's main commission — 20% of the bill.
- **GST on fees (R):** 18% GST charged *on top of* the Swiggy fees themselves.
- **Collection Charges (M):** fee for collecting the customer's money.
- **Access Charges (N):** token-card/delivery-access surcharges.
- **Long Distance Subscription Fees:** extra when order travels far.
- **Swiggy One Fees (J):** from Swiggy One membership orders.
- **Pocket Hero Fees (K):** Swiggy's own delivery service fee.
- **Bolt Fees (L):** "Bolt" lightning-delivery fee.
- **Merchant Cancellation Charges (O):** penalty when an order is cancelled
  (even when the customer did it, or it was out of Mom's control).
- **Call Center Service Fees (P):** fees for phone-order handling.
- **Delivery fee sponsored by merchant (U1):** time Swiggy charged the delivery
  fee back to the restaurant.
- **TCS / TDS:** statutory levies, not Swiggy's money — verify, but these are
  tax; the complaints are about the fee lines above.
- **MFR policy:** "Merchant Fee Refund" (MFR_AND_ECOM_POLICY) — claimed refund
  when the platform's own policy applies (e.g. customer-cancelled or not
  picked-up orders).

### B.4 Zomato

- No Zomato fee annexure export is available yet — Zomato charges commission
  too, plus GST on commission, online payment fees, surge/dark-store fees and,
  importantly, **promotions the platform auto-applies to the customer and later
  bills the restaurant for**.
- What we know from July: **140 orders / ₹62,066** customer spend.
- For Zomato complaints: ask for the **per-order**, **itemised** commission
  statement and the promotion-contribution report before signing off on any
  debit. Do **not** accept a lump-sum "adjustment" without the row-level
  breakdown.

### B.5 Which charges are the "random, without consent" ones

1. **LAST_WEEK_OUTSTANDING_CURRENT** claw-backs — no invoice, no consent,
   recurring. **Top priority.**
2. **TOP_PICKS_ADS / HIGH_PRIORITY / HOMEPAGE_BANNER / ADS_OFFERS** — ads
   charges where there is no record of the restaurant subscribing (and
   definitely no consent to auto-renew weekly).
3. **Merchant Cancellation Charges** applied to orders *not* cancelled by the
   restaurant or where policy refund should apply.
4. **Delivery fee sponsored by merchant** — a delivery fee silently pushed back
   onto the restaurant.
5. Any lump-sum "adjustment" debit that arrives with **no supporting invoice** —
   demand the invoice before accepting it.

---

## PART C — The new app (tulsifoods.app): exists, but not in her daily life yet

### C.1 What it is

A direct-ordering website + WhatsApp ordering system built to move Tulsi Foods
off Swiggy/Zomato's ~27–32% commission onto **direct** ordering, where the
restaurant keeps ~100% and can even charge the customer less.

- Live at: **https://tulsifoods.app** (and api.tulsifoods.app / menu etc.).
- Built by the family's developer son; deployed on **Railway**
  (railway.app). Docker container, Python (FastAPI), SQLite.
- **It does not yet exist in Mom's day-to-day routine.** Her kitchen still runs
  exactly as in Part A — Petpooja POS, Swiggy/Zomato apps, phone and WhatsApp
  calls. The app is being built and tested around her, not replacing anything
  yet.

### C.2 What already works on the new app (verified)

- Full menu (141 items, 10 groups) with real photos, "today" availability, and
  per-dish pages.
- Cart + checkout with:
  - **Delivery zones & fees:** A (≤3 km) ₹30 / B (≤5 km) ₹50 / C (≤7 km) ₹70;
    minimum order ₹250 / ₹300 / ₹350; over 7 km not served; free delivery
    over ₹700 is *disabled* for now.
  - **Packing fee:** ₹20 (₹40 on orders over ₹1,000) and **GST 5%**.
  - **Payment:** Cash on Delivery, or UPI to `tulsifoods@icici` (credit
    confirmed manually by the kitchen), or "pay the courier directly".
  - **Timing:** order "As soon as possible" or pick a **Lunch window**
    (12:00–2:30 PM) or **Dinner window** (6:30–9:30 PM); Monday opening is
    14:00. Orders are blocked outside opening hours.
- **Kitchen alert:** every new order pings Mom on **Telegram** (@tulsifoodsbot)
  and beeps in the admin panel — no app to open, works without WhatsApp
  approval.
- **Delivery:** live **Borzo** courier quotes, rider booking from the admin,
  and a customer **tracking page** with live rider status.
- **Admin panel** for the kitchen: order list, status buttons, availability
  toggles, "book a rider."

### C.3 What is still pending on the app (so the AI doesn't over-promise)

- **WhatsApp / Meta business verification** is still not approved — the
  business number (+91 99400 62840) remains `NOT_VERIFIED`; outbound WhatsApp
  templates can't be broadcast yet. (SMS fallback via Twilio is on a trial
  account that skips real sends until upgraded.)
- **Petpooja POS relay:** the site → Petpooja order push works and was fully
  verified in the sandbox (a test order went end-to-end: placed → accepted in
  the POS dashboard → statuses updated). It is **waiting on production
  credentials** from Petpooja and a **static egress IP** to be whitelisted
  (Petpooja requires it — before going live, enable Railway "Static Outbound
  IPs" under Pro plan settings and send all 3 assigned IPv4 addresses to
  Shivam Tiwari at Petpooja).
- So while the site works and test orders have run, **no real customer has
  been moved over yet** — direct-phone/WhatsApp ordering remains the live
  direct channel today.

### C.4 Why the app matters in the fee fight

- It is the **leverage**: an audited, working alternative channel. Every
  complaint email can (politely) note that the restaurant is building its own
  ordering channel because the platform's fees are unsustainable.
- It is the **data source**: once live, direct-order revenue proves the value
  the platform was taking (27.5%) compared to what direct retains (~100%).
- Its own numbers (delivery profile, order sizes, popular items) come from the
  same Swiggy/Zomato exports used in Part B — one set of records serves both
  the app and the complaints.

---

## PART D — Writing complaint emails for Mom (playbook)

### D.1 Golden rules

1. **One issue, one email.** Don't bundle the ads and the claw-back into one
   giant rant; separate complaints get separate tickets and get resolved faster.
2. **Always carry receipts.** Order No., date, amount, line-item label — from
   Part B. No invented figures, ever.
3. **Ask for specific relief:** "Please credit ₹X back to my settlement" or
   "Please send the row-level invoice for this debit before 15 days."
4. **Set a deadline and next step** ("Share the breakdown by 7 days; if not,
   please escalate to your nodal officer").
5. **Firm but professional.** Swiggy/Zomato support staff escalate emails that
   are clear and numbered far more than angry ones.
6. **CC / keep the chain.** Always reply in the same ticket thread so dates and
   promises are on record.
7. **Escalate properly:** support portal → relationship/senior manager →
   nodal officer with a formal notice → (only if ignored) a consumer complaint
   with copies of everything. Each level mentions the next.
8. **Attach the file.** Cite the CSV name + row, and attach the actual export
   so the agent can verify.

### D.2 The data arsenal (what to quote)

| File | What's in it | Use for |
|---|---|---|
| `01_swiggy_orders_fee_annexure.csv` | Per-order fees, 938 orders | Commission/GST/collection math, cancellation charges |
| `02_swiggy_adjustments_ads_fees_annexure.csv` | The adjustments + ads debits | OUTSTANDING_CURRENT claws, TOP_PICKS_ADS, banners |
| `03_online_platforms_sales_jul2026.csv` | July sales by channel | "I sold ₹62,066 on Zomato — show me every fee" |
| Swiggy dashboard settlement screenshots | Weekly/fortnightly settlements | Cross-reference the claw-backs |
| Zomato partner dashboard (commission report) | Per-order commission | Zomato itemised questions |

Sample quoting line:
> "Row of `02_swiggy_adjustments_ads_fees_annexure.csv`: Adjustment Item
> `LAST_WEEK_OUTSTANDING_CURRENT`, period 2026-07-26 to 2026-07-28, amount
> **−₹5,404.47**. There is no supporting invoice for this debit. Please provide
> the per-order breakdown and credit it back."

### D.3 Email templates

#### Template 1 — the "LAST_WEEK_OUTSTANDING_CURRENT" claw-back (priority #1)

> **Subject:** Unauthorised debit of ₹13,539.36 (period 01–04 Aug 2026) — no
> invoice received — Settlement #RID 28173
>
> Dear Swiggy Partner Support,
>
> On 1–4 August 2026 my settlement was debited **₹13,539.36** under the line
> `LAST_WEEK_OUTSTANDING_CURRENT` (RID 28173). This is the eighth such
> "outstanding" debit in three months — earlier amounts include ₹10,545.66,
> ₹8,318.25, ₹7,373.68 and ₹5,404.47 — none of which was accompanied by any
> invoice or per-order breakdown.
>
> My restaurant (Tulsi Foods, Mylapore) has not been given any statement
> explaining what these amounts represent, nor did I consent to any such
> deduction.
>
> Please:
> 1. Provide a **row-level breakdown** (order number, date, amount) for each
>    `LAST_WEEK_OUTSTANDING_CURRENT` debit from May to August 2026;
> 2. **Credit back ₹77,141.13** (the total debited) or, if any portion is
>    genuinely payable, show me the exact invoice for that portion;
> 3. Confirm in writing that no further deduction under this label will occur
>    without a prior itemised invoice.
>
> Kindly share the breakdown and credit within 7 days. If this is not
> resolved, please escalate to your nodal officer.
>
> Regards,
> [Mom's name], Tulsi Foods, 34 Murrays Gate Road, Alwarpet, Chennai 600018
> Phone +91 99406 21800 · WhatsApp +91 99400 62840 · GSTIN [if set]
> Attachment: `02_swiggy_adjustments_ads_fees_annexure.csv`

#### Template 2 — auto-renewing ads without consent (TOP_PICKS_ADS etc.)

> **Subject:** Ad charges deducted without my consent — TOP_PICKS_ADS
> (₹4,056.25), HIGH_PRIORITY (₹1,766.65), HOMEPAGE_BANNER (₹824.12)
>
> Dear Swiggy Partner Support,
>
> My settlement statement shows recurring deductions for advertising that I
> did not subscribe to or renew:
> - `TOP_PICKS_ADS` — **₹368.75 every week** from 17 May to 8 Aug 2026
>   (total **₹4,056.25**);
> - `HIGH_PRIORITY` / `HOMEPAGE_BANNER` / `ADS_OFFERS` — a further ₹2,593.13.
>
> I have never opted into these campaigns, and I have not authorised any
> auto-renewal. Please:
> 1. Share the campaign opt-in record and the supporting invoice for each of
>    the above deductions;
> 2. **Credit back the full ₹6,649.38** if my consent cannot be shown;
> 3. Confirm these programmes are now **switched off** and will not restart
>    without my explicit approval.
>
> Amounts are as per the attached `02_swiggy_adjustments_ads_fees_annexure.csv`.
> Please respond within 7 days; otherwise I request escalation to your nodal
> officer.
>
> Regards, Tulsi Foods (as above)

#### Template 3 — commission / fee-math audit (per the annexure)

> **Subject:** Request to audit Platform Service Fee and GST on fees — 938
> orders (May–Aug 2026)
>
> Dear Swiggy Partner Support,
>
> My per-order export shows total customer billings of **₹3,93,398.67** for
> 938 orders (May 5 – Aug 12 2026), from which Swiggy deducted **₹1,08,158.20**
> in fees — including Platform Service Fee of ₹78,548.82 (20%), Collection
> Charges of ₹7,841.40, and 18% GST charged on the fees themselves — leaving
> the restaurant ₹2,63,477.92 (≈67% of the bill).
>
> Please confirm that every per-order deduction in the attached
> `01_swiggy_orders_fee_annexure.csv` matches your commission policy, and
> flag and refund any amount that does not. In particular I want confirmation
> on:
> 1. Platform Service Fee computed on the correct base (net bill value, not
>    after any free-delivery discount adjustments);
> 2. GST at 18% applied only to fees chargeable under GST;
> 3. Collection/Access charges applied only where actually incurred.
>
> Please provide your review within 10 days, with a refund for any
> discrepancy. If I do not hear back, I will escalate.
>
> Regards, Tulsi Foods (as above)

#### Template 4 — merchant cancellation charges

> **Subject:** Disputed Merchant Cancellation Charges (₹1,998.48) — orders not
> cancelled by the restaurant
>
> Dear Swiggy Partner Support,
>
> My export lists `Merchant Cancellation Charges` of **₹1,998.48** across the
> May–Aug 2026 period. Several of these orders were cancelled by the customer
> or never picked up by the rider (cancellation by "CUSTOMER"/"not picked up"
> in my records) and should fall under your MFR/cancellation-policy refund.
>
> Please audit the cancellations in `01_swiggy_orders_fee_annexure.csv`, refund
> any charge on orders the restaurant did not cause to be cancelled, and
> confirm the policy applied to each. Respond within 10 days.
>
> Regards, Tulsi Foods (as above)

#### Template 5 — Zomato: request for itemised statement

> **Subject:** Request for itemised commission & settlement statement — July
> 2026 (140 orders, ₹62,066)
>
> Dear Zomato Partner Support,
>
> In July 2026 my restaurant fulfilled **140 orders worth ₹62,066** through
> Zomato. I have no per-order breakdown of the commission, GST on commission,
> online-payment fees, promotion contributions, or any adjustments deducted
> from my settlement.
>
> Please provide:
> 1. A **per-order commission statement** for July 2026;
> 2. Full detail of any promotion costs applied to my account, with proof of
>    my opt-in; and
> 3. A reconciliation of my settlement amount to these charges.
>
> I expect itemised clarity before any further deduction. If I do not receive
> it within 10 days, please escalate to your nodal officer.
>
> Regards, Tulsi Foods (as above)

#### Template 6 — follow-up / escalation (use when a template receives no reply)

> **Subject:** ESCALATION — [Original subject]
>
> I wrote to you on [date] regarding [amount + charge]. As of today I have not
> received the itemised breakdown or refund requested. Please:
> 1. Acknowledge and resolve this within **5 days**, or
> 2. Escalate to your nodal officer and copy me on that referral.
>
> If the matter remains unresolved after that, I will proceed with a formal
> consumer complaint attaching this correspondence and my settlement records,
> as permitted under applicable law.
>
> Regards, Tulsi Foods (as above)

### D.4 Escalation ladder (tone gets firmer, facts stay identical)

1. Partner support portal / email (templates 1–5) → 7–10 days.
2. Senior / relationship manager — same content + "escalate to nodal officer."
3. Nodal officer notice (template 6) with everything attached.
4. Regulated complaint (consumer forum / appropriate authority) — only as a
   genuinely last step, with the full audit trail.

### D.5 What "good" looks like

- A row-level breakdown that *explains* every debit (proves it wasn't a
  rounding error on their side) **or** a credit back to the settlement.
- Ads either proven as opted-in (and then cancelled going forward) or refunded.
- A written confirmation that future deductions require an itemised invoice
  sent **before** the debit.

---

## Appendix — Quick reference numbers card

| Fact | Number |
|---|---|
| Swiggy fees as % of customer spend (May–Aug 26) | **27.5%** (₹1,08,158 on ₹3,93,398) |
| Restaurant net of Swiggy cut | **67.0%** (₹2,63,477) |
| July example (customers paid / netted) | ₹1.47 lakh / ₹99.6K |
| `LAST_WEEK_OUTSTANDING_CURRENT` debits | 9 × ₹77,141 total (each ₹5.4K–₹13.5K) |
| `TOP_PICKS_ADS` weekly fee | ₹368.75 × 11 = ₹4,056.25 |
| Other ad charges | HIGH_PRIORITY ₹1,766.65 · HOMEPAGE_BANNER ₹824.12 · ADS_OFFERS ₹2.36 |
| Swiggy July orders / value | 322 / ₹1,44,108 |
| Zomato July orders / value | 140 / ₹62,066 |
| Median order value | ₹286 (51% under ₹300) |
| Median delivery distance | 2.4 km (67% ≤3 km) |
| Channel mix (May–Aug 26) | ~65% direct / ~35% online |
| Top sellers | Phulka, Sabudana Vada, North Indian & Mini Thali, Masala Chai |
| Direct-app delivery zones | A ≤3km ₹30 · B ≤5km ₹50 · C ≤7km ₹70 (min ₹250/300/350) |
| Direct-app packing / GST | ₹20 (₹40 ≥₹1,000) / 5% GST |
| Direct-app UPI | tulsifoods@icici (manual confirm) |
| Petpooja | POS; ₹3,000/yr; relay verified on sandbox, prod creds + static-IP pending |
| App infra | Railway (tulsifoods.app); no real customers moved yet |