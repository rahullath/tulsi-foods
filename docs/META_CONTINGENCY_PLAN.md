# Contingency Plan — If Meta Business Verification Keeps Lagging

**Status:** Planning doc. Not yet approved/built.
**Date:** 2026-08-30
**Premise:** The whole direct-ordering stack (website → order → kitchen → status → WhatsApp notifications) currently routes through the app's own admin + WhatsApp, which is gated behind Meta Business verification. If Meta drags on, we don't want the ordering system to stay blocked. This plan decouples **kitchen fulfillment** and, partially, **customer notifications** from Meta.

---

## 1. What Meta is currently blocking (and what it is NOT)

Blocked by Meta verification:
- **WhatsApp template messages** (the pre-approved `order_*` / `delivery_update_*` templates) — can't be broadcast until verification completes. We already call them but they fall back to plain text.
- **Registering the +91 99400 62840 number / real sends** — currently `NOT_VERIFIED`; the live webhook works but real outbound needs the number registration step after verification.

NOT blocked by Meta (already working, independent of Meta):
- The **website + ordering flow + admin dashboard** (FastAPI on Railway) — fully live.
- **Order intake, cart, checkout, payment intent** (COD/UPI via the order flow; Cashfree researched but not built).
- **Borzo delivery dispatch + tracking** — production CMS token, callback re-pointed to `tulsifoods.app`.
- **In-app admin order state machine** (preparing → ready → dispatched → delivered/cancelled), via `db.update_order_status()` + admin UI.
- **Petpooja spec** — a two-way POS relay (details in §3).

So the truly-Meta-blocked piece is only **outbound WhatsApp notifications**. Everything that makes an order *get made and delivered* can run on Petpooja + Borzo without Meta.

---

## 2. Recommended sequence (unblocks the most, fastest)

1. **Add Petpooja's website order relay (§4)** — allows PoS Accept/Reject to drive status. This replaces the "kitchen uses our admin" manual step with the motion mom already does for Swiggy/Zomato. Highest leverage.
2. **Add the Petpooja → us → Borzo rider webhook chain (§6)** — when PoS says "Food Ready / Dispatch", auto-dispatch Borzo, no admin click.
3. **Dual-track customer notifications (§7)** — continue trying WhatsApp templates when verification lands, but add an **SMS fallback** (via the already-exists UPI/order infra or an SMS provider) + **order-tracking page** so customers aren't blind until Meta approves.
4. Revisit Meta later — nothing here prevents verification from completing; it just stops Meta from being on the critical path.

---

## 3. What Petpooja actually gives us (from `temp/petpooja-api.txt`, not committed)

Petpooja's Online Ordering API (V2.1.0) is a **two-way relay** between our site and her POS (the system that already receives Swiggy/Zomato):

- **`Save Order`** (we → Petpooja, POST to a Petpooja-hosted URL): pushes a website order into her POS as a **new order in Pending state**. She accepts/rejects it with the exact same motion she already uses for Swiggy/Zomato. (spec, line 193)
- **`Order Callback`** (Petpooja → us, a webhook *we host*; its URL is passed in every Save Order call): sends `status` updates:
  - `-1` = Cancelled
  - `1/2/3` = Accepted
  - `4` = Dispatch
  - `5` = Food Ready
  - `10` = Delivered
  - Plus `rider_name` / `rider_phone_number` on Dispatch (spec, lines 405-421).
- No self-serve signup — `app_key` / `app_secret` / `access_token` / `restID` are issued by Petpooja after registering. There is a staging env (`developerapi.petpooja.com`). Contact: **Malvi Vaghela**, ₹3,000/outlet/year ex-GST.

Status mapping to our internal statuses:
| Petpooja | Ours |
|---|---|
| 1/2/3 Accepted | `preparing` |
| 5 Food Ready | `ready` (delivery) / `ready` pickup |
| 4 Dispatch | `dispatched` (then trigger Borzo) |
| 10 Delivered | `delivered` |
| -1 Cancelled | `cancelled` |

These map cleanly onto `db.update_order_status(order_id, status)`.

---

## 4. Phase 1 — Petpooja order relay (kitchen independence)

Goal: a website order lands in her POS and is made/delivered regardless of Meta.

New code (all in the existing FastAPI app — reuses the proven webhook pattern from `app/webhooks.py`):

- **`app/petpooja.py`** — client mirroring `app/delivery/borzo.py`: `save_order(...)` (POST to Petpooja's `save_order` URL with `app_key`/`app_secret`/`access_token`/`restID` + order + `callback_url`), plus helpers to transform an internal order into Petpooja's `OrderInfo/Customer/Order/OrderItem/AddonItem/Tax/Discount` nesting.
- **Config** (`app/config.py` or `app/delivery/config.py`): `PETPOOJA_*` env vars (`APP_KEY`, `APP_SECRET`, `ACCESS_TOKEN`, `REST_ID`, `SAVE_ORDER_URL`, and staging vs prod switch).
- **Trigger**: on website order creation (the same place COD/order records are written), call `save_order`. Keep the order's internal `order_id` as `clientorderID` so callbacks map back.
- **`app/webhooks.py` → `POST /webhook/petpooja/order_callback`**: parse the callback body, map the Petpooja status per §3, call `db.update_order_status(order_id, mapped)`, and — as today — `_send_status_whatsapp_if_needed()` (which gracefully falls back to plain text until Meta approves).
- **`update_order_status`** in reverse: when an order is cancelled from the website/admin, call Petpooja's `update_order_status` (`status=-1`) so the POS stays consistent (spec, lines 429-472; `orderID` deprecated → pass blank, use `clientorderID`).

Why this is safe:
- It's the *same* Pending→Accept/Reject queue she already uses; no new workflow, no risk of a rogue order printing without her approval.
- Versioned under the existing `app/webhooks.py`/`db.py` conventions — consistent with Borzo, so reviewer guidance already exists.

## 5. Phase 1 prerequisites (user action, not code)

- Ask **Malvi/Petpooja** for **staging credentials** (`app_key`, `app_secret`, `access_token`, `restID`) + the current Save Order / dev URLs. Per the spec, the dev URLs are:
  - Fetch menu: `https://qle1yy2ydc.execute-api.ap-southeast-1.amazonaws.com/V1/mapped_restaurant_menus`
  - Save order: `https://47pfzh5sf2.execute-api.ap-southeast-1.amazonaws.com/V1/save_order`
  - Update order status / rider webhook: `https://qle1yy2ydc.execute-api.ap-southeast-1.amazonaws.com/V1/...`
  - ⚠️ Apiary docs host is retired **Oct 31 2026** — get docs from `developerapi.petpooja.com` going forward.
- Confirm the exact `OrderInfo/Order` field shapes with a live staging `save_order` before finalizing the transformer (the apiary spec is high-level; real payloads are authoritative).

---

## 6. Phase 2 — Petpooja → Borzo delivery chain (auto-dispatch)

Once Phase 1 has her accepting website orders in the POS:

- On `Order Callback` with status `5` (Food Ready):
  - Call `admin_dispatch_order`-equivalent → **Borzo `create_order`** (already production-ready with the CMS token). This removes the manual "Food Ready → dispatch" admin click, since dispatching becomes: site order → POS accept → Food Ready → auto-Borzo.
- On `Order Callback` status `4` (Dispatch) — Petpooja also sends `rider_name`/`rider_phone_number`:
  - If it's a **self-delivery** rider, forward that to the customer; if Borzo dispatched, rely on Borzo's tracking instead.
- Forward **Borzo delivery events → Petpooja's `rider_status_update` webhook** (spec lines 513-577; `status` = `rider-assigned` / `rider-arrived` / `pickedup` / `delivered`; pass `external_order_id` blank, use our `order_id`). This keeps her POS delivery timeline accurate without polling — same cost/pattern as the Borzo callback we already host.
- Optional Phase-2 add-ons (from spec): Item/Addon **In/Out of Stock** sync (Petpooja → us to auto-update `db.set_availability()`), **Push Menu** (replace hand-maintained `data/menu.json`), and store open/closed sync.

## 7. Phase 3 — Customer notifications without Meta

Goal: customers get order updates even though Meta templates are on hold.

> **Reality check on the number:** WhatsApp Cloud API does **not** issue us a
> number — we use Mom's existing **+91 99400 62840**. Petpooja changes
> nothing there. The only blocker is Meta finishing business verification, which
> flips that number's `code_verification_status` to VERIFIED. There is no
> "Meta gives us a number" shortcut; it's verify-our-own-number once review
> clears. So Phase 3 only matters while that review is stuck.

- **Order tracking page**: a simple `GET /track/{order_id}` that reads `db.get_order()` and shows current status (+ Borzo courier location when dispatched). Messages link to it. This is the durable, always-available status surface and the **primary non-Meta notification** — cheap, no sender-ID/DLT, works for every customer.
- **Twilio SMS fallback (built, kept as secondary)**: `app/sms/twilio.py` + a `notify()` dispatcher (`app/notify.py`) already route status/dispatch messages to Twilio when `WHATSAPP_ACTIVE` is off, and flip to WhatsApp templates when `WHATSAPP_ACTIVE=1`. Kept and wired now.
  - ⚠️ **Cost/effort reality (why SMS is NOT the answer long-term):** Twilio is currently a **trial** account — verified-recipient-only + pre-defined-content-only (error 572006). Real customer SMS needs an **upgrade** + an **Indian DLT sender ID** registration + ~₹0.30–0.50/message, vs WhatsApp in-conversation **free** and utility templates ~₹0.12. So SMS is strictly a short stopgap, not a replacement — WhatsApp remains the real channel. Priorities: Petpooja + tracking page first, SMS last.
  - This matches the current code: `WHATSAPP_ACTIVE` (in `app/config.py`) defaults off → SMS; flip to `1` post-verification to go WhatsApp.
- **Keep attempting WhatsApp**: templates + `notify()` already wired; only env vars change post-verification (no code) per ROADMAP §C.

---

## 8. What this does NOT change

- **Meta remains the long-term WhatsApp channel** (free service conversations, no BSP markup). This plan is purely additive — it removes Meta from the *critical path* but doesn't abandon it.
- **The ordering UX** (menu/cart/checkout/COD/UPI) is unchanged; Petpooja sits under the hood as the kitchen relay.
- **Borzo delivery** is unchanged — already production-ready.

## 9. Open decisions for you

1. **Pay for Petpooja now?** ₹3,000/outlet/year ex-GST, contact Malvi. Recommend: only after we confirm it's actually the POS in use and get staging creds to build-then-verify (not pay-and-hope).
2. **SMS provider choice** (Phase 3) — MSG91 vs Twilio vs Textlocal; needs an account + sender-ID registration.
3. **Do we want auto-dispatch (Phase 2) or keep the human "confirm ready" click as a safety check for the first few weeks?**

## 10. Suggested next step

Ask Malvi for **staging Petpooja credentials** first (free, no commitment). With staging keys we can build and verify the Phase-1 relay end-to-end against real POS payloads before spending any money — matching how we handled Borzo (test-then-enable).
