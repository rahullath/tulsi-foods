# Petpooja POS Integration — Status & Go-Live Checklist

Last updated: 2026-09-05, after a full sandbox testing session (staging restID
`qa3xsbk42g`, "Tulsi Foods" demo restaurant). Read this before touching
`app/petpooja/` or flipping to production credentials — it captures what's
verified, what's fixed, and what's still open so going live doesn't mean
re-discovering the same bugs.

Contact: Shivam Tiwari (Associate PM), Malvi Vaghela / Rohan Sakhrani for
API support (`malvi.vaghela@petpooja.com`, `rohan.sakhrani@petpooja.com`).

---

## 1. What's done and verified (staging)

- **Credentials wired**: `.env` (local) and Railway (production env) both
  have `PETPOOJA_APP_KEY` / `PETPOOJA_APP_SECRET` / `PETPOOJA_ACCESS_TOKEN` /
  `PETPOOJA_REST_ID` (= `qa3xsbk42g`) / `PETPOOJA_WEBHOOK_TOKEN` set. Confirmed
  by a real order (`order_id=15`) auto-relaying from the live server the
  moment it was placed.
- **All 5 of Petpooja's required test scenarios** (Shivam's email, Sep 4) —
  verified correct against the live sandbox, including Grand Total math:
  Items+Tax, Item+Addon+Tax, Item+Variation+Tax, Item+Discount+Tax,
  Item+Addon+Variation+Tax. Order IDs sent back to Petpooja for review.
  Reproducible via `python3 -m scripts.petpooja_test_orders`.
- **Full order lifecycle, on a real production order** (`order_id=15`,
  pickup, "North Indian Thali"): placed via `/api/orders` → auto-relayed to
  Petpooja (Save Order) → Accepted in the sandbox dashboard → our order
  flipped `new → preparing` via the `/webhook/petpooja/order-callback` →
  "Food Ready" clicked → flipped `preparing → ready`. Both callback legs
  confirmed end-to-end against the *live* Railway deployment, not just
  locally.
- **Webhook auth was silently disabled in production** — `PETPOOJA_WEBHOOK_TOKEN`
  wasn't set on Railway, so `_check_petpooja_token()`'s `if PETPOOJA_WEBHOOK_TOKEN`
  guard was a no-op and any token (or none) was accepted. Fixed by adding the
  var to Railway; confirmed a wrong token now gets a real `403`.

## 2. Bugs fixed this session (in `app/petpooja/`)

All in [mapping.py](../app/petpooja/mapping.py) unless noted:

- Order-level `Tax.details` was sent as `[]` — added the required
  CGST/SGST breakdown with `restaurant_liable_amt`.
- Per-item `tax_percentage` field was missing entirely.
- `discount_total`/`discount_type` were hardcoded to `"0"`/`"F"` regardless
  of the order — now pulled from the order dict.
- **`enable_delivery` was backwards**: old logic was
  `1 if order_type == "delivery" else 0`, but this field means "who
  delivers" (`0`=third-party rider, `1`=restaurant's own rider), not
  "is this a delivery order". Every Tulsi Foods delivery goes through Borzo
  (third-party) — confirmed wrong because every test order's sandbox receipt
  showed "Home Delivery **(Self delivery)**". Now hardcoded to `0`.
- **Addon items silently dropped**: the flat `"addon_items"` key (from
  Petpooja's newer Sep 2026 API guide) is not read by this sandbox — an
  addon-bearing order saved fine but the addon never appeared on the
  receipt. Fixed by *also* sending the older Apiary shape,
  `"AddonItem": {"details": [...]}`, alongside it. Never isolated which key
  the backend actually reads since both were sent together — harmless to
  keep sending both indefinitely.
- Per Petpooja's guide ("price = item unit price + addon price"), an
  item's `price`/`final_price` must already include its addons' cost —
  `scripts/petpooja_test_orders.py` didn't do this originally, so addon
  cost was silently excluded from the Grand Total. Fixed in the test script.
- [config.py](../app/petpooja/config.py): `PETPOOJA_SAVE_ORDER_URL` default
  pointed at a different, unconfirmed API Gateway host
  (`47pfzh5sf2...`) than the other three endpoints and the real sandbox
  dashboard (`qle1yy2ydc...`). Fixed to match.
- [client.py](../app/petpooja/client.py) `save_order()` now also returns
  `client_order_id`/`message` — the sandbox's own `orderID` comes back
  **blank on every successful save**, confirmed consistently across dozens
  of calls. The dashboard's Order Listing search is keyed on `clientOrderID`
  (our own order id), not their internal one — use that for lookups.
- **`price`/`final_price` were qty-scaled, should be per-unit.** The API
  guide's worked example is explicit that quantity is not multiplied into
  these two fields (the qty-scaled total is carried separately in the
  order-level `total` key) — `final_price = price - item_discount`. Fixed
  2026-09-07.
- **`preorder_date`/`preorder_time` were hardcoded to `""`.** The guide
  states these must mirror `created_on` whenever `advanced_order` is `"N"`
  (which is always, for us). Fixed 2026-09-07.
- **`Order.details.total` included `delivery_charges` — wrong per the
  official API guide.** Its field definition is explicit: *"Total = Item
  Final Price [- Order level Discount] + GST [if liable by restaurant] +
  Packing Charges. The 'Total' should only include the amount due to the
  restaurant."* Delivery money belongs to Borzo, not us, so it must be
  excluded — every order was overstating restaurant revenue to Petpooja's
  own settlement/accounting by the delivery fee. Fixed 2026-09-07: `total`
  is now `subtotal - discount_total + gst_amount + packing_fee`, computed
  separately from `collect_cash` (which correctly stays the full
  customer-facing amount, delivery included, since that's what's literally
  collected on COD).
- **`pc_tax_percentage` was hardcoded to `"0"` despite being a required
  field** (confirmed by the official API guide's field table) **and despite
  packing genuinely being taxed** in our model (folded into `gst_for()`'s
  taxable base). Fixed 2026-09-07: now `gst_rate * 100`, with
  `pc_tax_amount` prorated from `gst_amount` the same way item-level tax is
  — this was §3.4 below; now resolved. (`dc_tax_percentage` staying `"0"`
  is *not* a bug — delivery is genuinely untaxed in our model, a Borzo
  pass-through outside the taxable base.)
- **`AddonItem.details` entries were missing `group_name`/`group_id`**
  entirely in `scripts/petpooja_test_orders.py`'s two addon scenarios (the
  reference payload shows both as present, `group_id` explicitly as an int
  not a string). Fixed 2026-09-07 with a placeholder `group_id` (real
  Petpooja addon-group ids are blank in `data/petpooja_addons.csv`, same
reconciliation gap as item ids, §3.2) and the real `group_name` from that
   CSV. Only affected the test script, not `mapping.py` — real orders never
   carry addons (no addon feature exists in the live product).
- **`Discount.details` was always sent as `[]`.** The docs' Save Order example
  carries the order-level discount there (mirroring `Order.details.discount_total`).
  Fixed 2026-09-12: populate a `{id, title, type, price}` block whenever
  `discount_total > 0`. Test scenario 4 now exercises it.

## 3. Known gaps — must resolve before going live

Ranked by how much it'll hurt if skipped.

### 3.1 Order cancellation/status changes on OUR admin side never reach Petpooja
`app/main.py`'s `POST /api/admin/orders/{id}/status` (used by `/kitchen` and
any admin UI) allows `new/preparing → cancelled` and other transitions, but
**only updates our own DB and sends the customer a WhatsApp** — it never
calls `petpooja.client.cancel_order()` (the Update Order Status API,
`status: "-1"`). `cancel_order()` exists and is fully written but is
**dead code — nothing in the app calls it**.

Concretely: if the kitchen cancels an order on the `/kitchen` tablet, or
walks it through `preparing → ready → out_for_delivery → delivered`,
Petpooja's own Order Listing will sit frozen at "Waiting For Acceptance"
forever, out of sync with reality. Confirmed the callback *inbound* path
(Petpooja → us) works; this is the missing *outbound* counterpart
(us → Petpooja) for anything other than the initial Save Order call.

**Fix before go-live**: wire `admin_update_order_status()` (and wherever
else order status changes — e.g. the WhatsApp cancel flow if one exists)
to call `petpooja.client.cancel_order()` when transitioning to `cancelled`,
guarded by `is_configured()` and `if o.get("petpooja_order_id") is not None`
(mirror the existing pattern in `webhooks.py`'s
`_relay_rider_status_to_petpooja`). Note `cancel_order()` currently only
supports status `-1`; the Update Order Status API's docs should be
re-checked for whether it also accepts forward-progress statuses
(preparing/ready/dispatched) or whether those are Save-Order-callback-only
in the other direction.

### 3.2 Menu/item ID reconciliation — still using placeholder IDs
Every order relayed so far (including the 5 test scenarios and real order
`15`) used item/addon/variation IDs we invented (`1001`, `2001`, `3001`,
or our own `data/menu.json` item slugs like `"north-indian-thali"`) — **not**
Petpooja's real catalog IDs. This is a pre-existing gap flagged in
`mapping.py`'s docstring since before this session; still unresolved.

- Tried `fetch_menu()` against the sandbox this session: got back
  `{"success":"0","message":"unable to fetch Object from s3 bucket"}` — no
  menu has been configured for restID `qa3xsbk42g` yet on Petpooja's side.
- The dashboard's Configuration page has **Type: Menu Push** selected
  (not Menu Fetch) — meaning Petpooja is supposed to push their catalog to
  *our* Menu Sharing Endpoint (`/webhook/petpooja/menu`), not the other way
  around. That webhook exists in `webhooks.py` and just caches whatever it
  receives to `data/petpooja_menu_raw.json` — **nothing reconciles it against
  `data/menu.json` yet.**
- **Before production**: (a) get Petpooja to actually push a real menu (or
  configure/trigger it from the dashboard's Menu Management → Menu Trigger),
  (b) write the reconciliation step that maps our `data/menu.json` item ids
  → Petpooja's real catalog item/addon/variation ids, (c) have
  `order_to_save_order_payload()` use the real ids. Untested whether the
  sandbox's leniency about fake ids (everything we sent "succeeded") will
  hold in production — production POS terminals may reject orders
  referencing items outside their actual catalog.

### 3.3 Order *modification* — behavior undocumented, unhandled
The Order Callback payload includes an `"is_modified": "No"/"Yes"` field
that our `/webhook/petpooja/order-callback` handler completely ignores
(only reads `orderID` and `status`). Neither Petpooja PDF in `temp/`
documents what a `is_modified: "Yes"` callback actually contains — full
updated item list? Just a flag with no detail? Unknown. **Ask Petpooja
support directly** (this is exactly what malvi.vaghela@petpooja.com is for)
before assuming a shape and building against it blind.

### 3.4 ~~Packing charge tax fields are internally inconsistent~~ — fixed 2026-09-07
`gst_for()` in `app/orders.py` computes GST over `subtotal + packing_fee`
(packing IS taxed, folded into the overall `gst_amount`), and that
prorates correctly into each item's `item_tax`/`tax_percentage` — confirmed
against a real packing charge (order 15: ₹20 packing folded into a ₹268
taxable base, CGST/SGST 6.70 each, matched exactly). The *separate*
`pc_tax_percentage`/`pc_tax_amount` fields in `Order.details` were
hardcoded to `"0"` regardless — now fixed (see §2) to prorate the same
way. Still not verified against a real sandbox order since the fix — worth
one more test-order run before going live, and still worth confirming with
Petpooja support that this reconciles with their own GST filing/reporting,
since it's the kind of thing that only surfaces at tax-filing time.

### 3.5 Untested against the sandbox (code exists, never exercised)
- **Rider Info API** (`push_rider_status` in `client.py`) — wired to the
  Borzo webhook relay (`_relay_rider_status_to_petpooja` in `webhooks.py`)
  but never actually fired against the sandbox this session.
- **Update Order Status / cancel** (`cancel_order`) — see 3.1, also just
  never called at all yet, sandbox or otherwise.
- **Item On/Off, Store On/Off webhooks** — endpoints exist
  (`/webhook/petpooja/stock`, `/webhook/petpooja/store-status[/update]`)
  but need the dashboard's Configuration page fields filled in first
  (Menu Sharing / Get Store Status / Update Store Status / Item Off / Item
  On endpoints — all under Base URL `https://tulsifoods.app/webhook`, each
  with `?t=<PETPOOJA_WEBHOOK_TOKEN>`). Not confirmed done as of this
  writing.

### 3.6 Production credentials will be different
The sandbox guide is explicit: staging App Key/Secret/Access Token/restID
are sandbox-only, separate ones get issued for production, and — per
`config.py`'s existing comment — **production URLs may differ from staging
too**. When Petpooja approves the review and sends production details:
update all `PETPOOJA_*` env vars (local + Railway) and re-verify the
staging URLs in `config.py`'s defaults still apply, or override via env if
not.

### 3.7 Static egress IP REQUIRED for production (Shivam, Sep 16 — confirmed)
The sandbox guide said the dashboard is IP-restricted, and Save Order API calls
succeeded from a local machine and from Railway's servers (different IPs,
neither of which is the `188.29.111.40` originally shared), so we suspected the
restriction applied only to *dashboard login*. **Shivam Tiwari's Sep 16 email
removes that doubt**: a static IP is required for the *live* integration so
Petpooja can verify every order-placement request originates from one. Treat
production Save Order as IP-whitelisted; don't plan around it "just working".

**Our infra (confirmed 2026-09-17):** the live site runs on **Railway** —
`tulsifoods.app` CNAMEs to `u0tbzotf.up.railway.app`; edge headers
`server: railway-hikari`, `x-railway-edge: lhr1`. The Fly.io app
(`tulsi-foods`) found on the dev machine is a **stale, suspended leftover**
(trial ended Aug 2026) — do not touch it; ignore the old `_fly-ownership` DNS
record and the `66.241.125.250` A record in `tulsifoods.app_dns_records.csv`
(they belong to the old Fly deployment). Railway deploy is Dockerfile-based,
EXPOSE 8000, via `git push`-triggered rebuild.

**Plan (go-live blocker):**
1. **Railway Pro plan required** for static outbound IPs ($20/mo, covers the
   first $20 of usage). Confirm the account already pays for Pro — if not,
   upgrade first.
2. In the Railway dashboard: Project → tulsifoods service → **Settings →
   Networking → Enable Static IPs** (Pro). No CLI needed (not installed on the
   dev machine). Traffic is load-balanced over the assigned IPv4s (3 by
   default since the July 2026 HA migration), so **Petpooja must whitelist ALL
   of them**, not one.
3. **Redeploy the service** after enabling — IPs only take effect after that.
4. Verify the machine really egresses from those IPs: Railway web-shell
   (dashboard → service → … → Shell) → `curl https://api.ipify.org`. Repeat a
   couple of times to confirm all 3 show up.
5. Email Shivam the full list of IPv4s for whitelisting (all of them, with the
   "3 addresses, load-balanced" note).
6. **Caveat — may be SHARED, not dedicated:** Railway's static outbound IPs
   are not guaranteed dedicated per-customer (they may be shared with other
   Railway Pro customers' egress). For Petpooja's stated need — *verify all
   order placement requests originate from a static IP* — a stable/static
   address is what matters and these qualify. If Shivam turns out to need a
   *dedicated* address instead, fallback is a tiny static-IP proxy/egress VPS
   (QuotaGuard ~$19/mo or a $5 VPS) and pointing `PETPOOJA_SAVE_ORDER_URL`
   traffic through it. Ask this explicitly in the reply.

## 4. Sandbox Dashboard — Endpoint Configuration

Per Shivam's email (Sep 2026): configure the following URLs in the Petpooja
sandbox dashboard under **Configuration → Endpoint**. The `Base URL` field
should be set to `https://tulsifoods.app/webhook`, and each endpoint path is
appended with the shared-secret token as a query param (`?t=...`).

The `?t=` token authenticates inbound calls from Petpooja (our
`_check_petpooja_token()` guard in `webhooks.py`). The token value is
`PETPOOJA_WEBHOOK_TOKEN` in `.env` / Railway.

| Dashboard field | Full URL |
|-----------------|----------|
| Base URL | `https://tulsifoods.app/webhook` |
| Menu Sharing Endpoint URL | `https://tulsifoods.app/webhook/petpooja/menu?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Get Store Status Endpoint URL | `https://tulsifoods.app/webhook/petpooja/store-status?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Update Store Status Endpoint URL (Store On) | `https://tulsifoods.app/webhook/petpooja/store-status/update?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Update Store Status Endpoint URL (Store Off) | `https://tulsifoods.app/webhook/petpooja/store-status/update?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Item On Endpoint URL | `https://tulsifoods.app/webhook/petpooja/stock?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Item Off Endpoint URL | `https://tulsifoods.app/webhook/petpooja/stock?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |
| Order Callback Endpoint URL | `https://tulsifoods.app/webhook/petpooja/order-callback?t=DzjxUqMROXJW--PlVd6i2jOx-EcvNbGK` |

Notes:
- Item On and Item Off share the same endpoint (the `inStock` boolean in the
  request body distinguishes them — see the API docs).
- Store On and Store Off also share the same endpoint (body has
  `store_status: 1` or `0`).
- Order Callback is already configured (tested end-to-end on order 15).
- **If `PETPOOJA_WEBHOOK_TOKEN` changes**, all URLs above must be updated too.

Response formats (all endpoints) match the API spec's 200 OK section —
verified 2026-09-12 against the rendered Apiary examples: Push Menu returns
`success: "1"` (string) + "Menu items are successfully listed.", Stock
toggle returns numeric `code: 200` + "Stock status updated successfully",
Get/Update Store Status return numeric `http_code: 200` with the documented
messages, and Order Callback returns an **empty 200 body** (their documented
response is `content-length: 0`). Get Store Status intentionally drops
`restID` to match the docs example.

## 5. Go-live checklist (do in roughly this order)

1. **Configure dashboard endpoints** (§4 above) — give the URL table to
   Shivam/Petpooja support to enter in the sandbox Configuration → Endpoint
   page.
2. Get Petpooja's review response on the 5 test scenario order IDs.
3. Ask Petpooja support to clarify 3.2 (menu push timing/format) and 3.3
   (`is_modified` payload shape) — both are blocking unknowns, not things
   we can resolve by guessing.
4. Fix 3.1 (wire admin cancel → `cancel_order()`) — straightforward, no
   external dependency, should happen regardless of Petpooja's answers.
5. Once Petpooja pushes/confirms a real menu: build the item/addon/variation
   ID reconciliation (3.2) and switch `order_to_save_order_payload()` over.
6. Test each endpoint by triggering from the dashboard (menu push, stock
   toggle, store status toggle) and confirming our handlers return the
   expected response format.
7. Fire one `push_rider_status()` and one `cancel_order()` call against the
   sandbox manually to confirm they don't error before relying on them live.
8. When Petpooja sends production credentials: swap `.env`/Fly secrets
   (`fly secrets set PETPOOJA_*`), update all endpoint URLs if production URLs
   differ, re-run `scripts/petpooja_test_orders.py` against production
   endpoints before taking real customer orders through it.
   - **Static egress IP is now a hard prerequisite (§3.7)** — enable Railway
     Pro static outbound IPs for the service, get all assigned IPv4s
     whitelisted with Petpooja and verified before production credentials
     land; production Save Order will reject others.

## 6. Reference

- Petpooja's two guide PDFs live in `temp/`: `Petpooja Sandbox Guide for
  Integration Testing.pdf` and `API Guide for Placing Orders on Petpooja
  POS.pdf` (Sep 2026) — these superseded the older Apiary docs
  (onlineorderingapisv210.docs.apiary.io) in a couple of spots (see §2).
- `scripts/petpooja_test_orders.py` — reproducible test-order generator for
  the 5 required scenarios; safe to re-run any time against staging (just
  regenerates unique client order IDs per run — **reusing an existing
  clientOrderID silently no-ops instead of updating the order**, confirmed
  the hard way, so don't hand-edit it to reuse old IDs when testing changes).
- `app/petpooja/mapping.py`'s module docstring has the item-id and
  GST-proration caveats inline; keep it in sync if 3.2/3.4 get resolved.
