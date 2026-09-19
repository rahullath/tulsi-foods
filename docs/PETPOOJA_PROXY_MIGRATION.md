# Petpooja Static-IP Proxy — Configuration, Issues & Clean Migration Guide

> **Situation:** Petpooja requires every order-placement request for the *live*
> integration to originate from a **static source IP** (Shivam Tiwari, email
> Sep 16 2026 — see `docs/PETPOOJA_INTEGRATION.md` §3.7). Railway's normal
> outbound IPs are dynamic, so we route **all outbound Petpooja API calls**
> through a dedicated proxy with a fixed IP instead of enabling Railway's
> per-service static egress IPs.
>
> **Status (2026-09-17):** Proxy chain is **verified end-to-end from
> Railway** — Squid auth + tunnel (`TCP_TUNNEL/200 CONNECT
> developerapi.petpooja.com:443`), egress (`200 35.209.244.171` via a
> temporary ipify allow), and all 5 test scenarios relayed through the proxy
> into the sandbox (`PPTEST-0917-12…` saved OK). **Production credentials
> were handed over the same day** (restID `84713`, endpoints on
> `pponlineordercb.petpooja.com`) — go-live steps in Stage C below.

---

## 1. The requirement (why this exists)

- Petpooja POS integration (web/WhatsApp direct orders → POS) is code-complete
  and sandbox-verified (order 15 lifecycle: place → POS accept → status
  callbacks). Production go-live is gated on: (a) production Petpooja
  credentials, (b) a static source IP they can whitelist.
- Petpooja's Shivam (Associate PM) confirmed a static IP is mandatory for live
  integration so they can verify order-placement requests.
- Solution chosen: a **dedicated HTTP proxy with a static public IP** that all
  outbound Petpooja traffic passes through. Requests egress from the proxy's
  fixed IP → whitelist that one IP with Petpooja.
- **Only Petpooja traffic is proxied.** Borzo, WhatsApp/Telegram, Twilio,
  Shiprocket and everything else continues to egress directly from Railway.
- Inbound webhooks (Petpooja → us: order-callback, menu push, stock/store
  toggles) are **not** affected by the proxy — they arrive on Railway directly.

---

## 2. Current configuration snapshot

### 2.1 The proxy

| Item | Value | Where |
|---|---|---|
| Env var | `PETPOOJA_PROXY_URL` | Railway (set), local `.env` (not yet) |
| Proxy URL (format) | `http://<user>:<pass>@<public-ip>:<port>` | — |
| Host / static IP | `35.209.244.171` (Google Cloud range) | rely on this IP for whitelisting |
| Port | `3128` (HTTP/Squid-style proxy) | — |
| Username | `railwayapp` | — |
| Password | contains an `@` character (`…5646@Tulsi…`) | see Issues I2 |

> **Do not paste the literal proxy URL into any committed file.** The
> password is a basic-auth credential. It lives only in Railway Variables and
> the local `.env` (gitignored). `.env.example` carries an **empty**
> placeholder.

### 2.2 Code wiring (applied, uncommitted as of this writing)

- `app/petpooja/config.py` — new:
  `PETPOOJA_PROXY_URL = os.environ.get("PETPOOJA_PROXY_URL", "")`
  (empty default = direct connections, correct for sandbox).
- `app/petpooja/client.py` — new `_client(timeout)` helper:
  ```python
  def _client(timeout: float) -> httpx.Client:
      return httpx.Client(proxy=PETPOOJA_PROXY_URL or None, timeout=timeout)
  ```
  All four outbound call sites now use it:
  | Function | Endpoint | Purpose |
  |---|---|---|
  | `save_order()` | `PETPOOJA_SAVE_ORDER_URL` | **order placement — the IP-whitelisted call** |
  | `cancel_order()` | `PETPOOJA_UPDATE_ORDER_STATUS_URL` | kitchen cancel → POS (−1) |
  | `fetch_menu()` | `PETPOOJA_FETCH_MENU_URL` | catalog pull (latent) |
  | `push_rider_status()` | `PETPOOJA_RIDER_STATUS_URL` | courier status → POS |
- The proxy applies automatically once `PETPOOJA_APP_KEY/_SECRET/_ACCESS_TOKEN/_REST_ID`
  are set (that gate is unchanged — `is_configured()`). Proxy is independent of
  which environment (staging/prod) the credentials belong to.

### 2.3 Config reference (all `PETPOOJA_*`)

| Var | Current value | Meaning |
|---|---|---|
| `PETPOOJA_APP_KEY` | (blank → set when prod issued) | issued by Petpooja |
| `PETPOOJA_APP_SECRET` | (same) | issued by Petpooja |
| `PETPOOJA_ACCESS_TOKEN` | (same) | issued by Petpooja |
| `PETPOOJA_REST_ID` | `qa3xsbk42g` in sandbox; **prod differs** | restaurant id |
| `PETPOOJA_SAVE_ORDER_URL` | default = staging host `qle1yy2ydc.execute-api…/V1/save_order` | prod may differ → override via env |
| `PETPOOJA_UPDATE_ORDER_STATUS_URL` | staging host | prod may differ |
| `PETPOOJA_FETCH_MENU_URL` | staging host | prod may differ |
| `PETPOOJA_RIDER_STATUS_URL` | staging host | prod may differ |
| `PETPOOJA_WEBHOOK_TOKEN` | (in webhook URLs we gave Petpooja) | inbound-auth token |
| `PETPOOJA_PROXY_URL` | **set in Railway** | this migration |
| `PETPOOJA_RES_NAME / _ADDRESS / _CONTACT` | Tulsi Foods / PICKUP_ADDRESS / PICKUP_PHONE | static store info |

### 2.4 What has been verified (log of tests, 2026-09-17)

| Check | Result |
|---|---|
| `httpx.URL(real_url)` parses host/port/user/pass correctly **despite `@` in password** | ✅ host=35.209.244.171 : 3128 |
| Behavior test, exact `@`-in-password shape, against a local mock proxy | ✅ request arrived at proxy as `POST http://target/save_order` (absolute-URI = proxied) |
| Behavior test, plain/`%40`/no-auth shapes | ✅ all proxied |
| Direct mode (`PETPOOJA_PROXY_URL` empty) | ✅ origin-form request, direct transport |
| `save_order()` returns parsed dict through both modes | ✅ |
| `py_compile` both files | ✅ |
| **Real proxy host `35.209.244.171:3128` connectivity from this dev machine** | ⚪ unreachable **by design** (Squid/GCP accepts Railway's egress range only) — see I1 |
| Squid auth + HTTPS tunnel to Petpooja, **from Railway** | ✅ `TCP_TUNNEL/200 CONNECT developerapi.petpooja.com:443` as `railwayapp` |
| Egress IP through the proxy, **from Railway** (`api.ipify.org`) | ✅ `200 35.209.244.171` (one-off temp Squid allow, then removed + restart → locked back to Petpooja-only) |
| The bare-GET 403 seen in testing | ⚪ **not Squid** — Petpooja's own app rejects unauthenticated `/` **inside** the tunnel; Squid completed the CONNECT and stepped out correctly |

---

## 3. Issues & gotchas found (read these before touching anything)

### I1 — 🟢 Proxy is reachable from Railway, not from the dev machine — **resolved**
`curl` and raw `CONNECT` to `35.209.244.171:3128` time out from dev **by
design**: Squid/GCP accepts only Railway's egress source range. Verified from
**inside Railway** (2026-09-17): authenticated tunnel `TCP_TUNNEL/200
CONNECT developerapi.petpooja.com:443` and egress echo `200 35.209.244.171`
(see §2.4 and Stage A). Cause was #1 in the original list — not a config problem.

**Keep in mind for local dev:** you cannot test proxy mode from the dev
machine; local tests must use direct mode (empty `PETPOOJA_PROXY_URL`) or a
local mock proxy.

### I2 — 🟡 The password contains an `@`
The literal URL is `http://railwayapp:5646@Tulsi@35.209.244.171:3128`
(user `railwayapp`, password `5646@Tulsi`).
- **httpx handles it correctly as-is** (splits userinfo on the last `@`) —
  verified both by URL parsing and a live mock-proxy round trip.
- **curl and RFC-strict tools reject it.** In Railway's web shell or any curl
  test you must either percent-encode the password
  (`http://railwayapp:5646%40Tulsi@35.209.244.171:3128`) or pass it via
  `--proxy-user 'railwayapp:5646@Tulsi'`:
  ```bash
  curl -s -x http://35.209.244.171:3128 --proxy-user 'railwayapp:5646@Tulsi' https://api.ipify.org
  ```
- **Do not "fix" the env value** — the stored string is correct for httpx.

### I3 — 🟡 Env values are read at import time
`client.py` does `from .config import PETPOOJA_PROXY_URL` once at module import;
the value is frozen for the process lifetime. That's exactly right for Railway
(env set before boot) but means:
- Changing the var requires a **redeploy/restart**, not just a dashboard edit.
- Local REPL/tests must set the env **before** importing `app.petpooja.*`.
- During a buggy first test, a stray **sandbox order (`order_id=45123`) was
  created** by hitting the real sandbox directly from the dev machine. It is
  harmless staging litter; being aware so it doesn't confuse the review of the
  5 required test scenarios.

### I4 — 🟡 Production credentials and prod URLs are still pending
The proxy does not depend on credentials, but go-live does. When Petpooja
issues production creds: set the four `PETPOOJA_*` credential vars **and**
confirm each endpoint URL — prod may differ from the staging host defaults
(which are bounded in `config.py`; override per-var via env if so).

### I5 — 🟡 Whitelist whatever IP Petpooja actually sees
The relevant IP is the one **the proxy presents** for outbound HTTPS — expected
`35.209.244.171`, but confirm with an echo (M4/M5) *through* the proxy, from
Railway. If the proxy ever has multiple egress IPs, whitelist **all** of them.
Railway-side static egress IPs are **not** involved in this design and should
stay disabled to avoid double-hopping.

### I6 — 🟠 Proxy is a single point of failure for order relay
All Petpooja calls now funnel through one host. Decide the failure behaviour:
- **Fail-fast (current):** proxy down → `save_order` raises after timeout →
  the site order still records locally, but no POS ticket prints. Telegram
  kitchen alert still fires (independent path), so the kitchen isn't blind.
- Recommended hardening (post-migration): a small uptime probe (TCP connect to
  `35.209.244.171:3128` every minute) with a Telegram/email alert; optionally
  automatic unset of the proxy env on repeated failures is **not** worth the
  complexity — prefer an alert + manual flip (I1 rollback path).

### I7 — ✅ Good news: the IPv6 egress gotcha is neutralised
Fly.io's "machines prefer IPv6 / whitelisted v4 gets bypassed" problem
(documented in §3.7) does **not** apply here: with a proxy the client never
resolves or connects to Petpooja directly — the proxy resolves and dials, and
its family/address is what Petpooja records. No client-side IPv4 pinning needed.

### I8 — 🟢 Non-issues already ruled out
- `trust_env`/global `HTTP(S)_PROXY`: none are set on Railway; when
  `PETPOOJA_PROXY_URL` is set it explicitly overrides any ambient proxy.
- Concurrency/threading: `_client()` creates one short-lived client per call
  (same as before); fine for 1 worker / low volume.
- Auth transport: basic auth goes to the proxy only; the Petpooja payloads are
  untouched (httpx forwards them verbatim over the tunnel).

---

## 4. Clean migration checklist (stage by stage)

### Stage A — Pre-flight on the sandbox (done 2026-09-17)
- [x] **A1. Proxy reachable from Railway.** Verified in the Railway web shell:
      `httpx.get('https://api.ipify.org', proxy=…)` → `200 35.209.244.171`
      (via a temporary Squid allow for `api.ipify.org`, then removed + Squid
      restarted → locked back to Petpooja-only).
- [x] **A2. IP is stable & survives a deploy.** Same `35.209.244.171` on
      repeat runs; the egress comes from the proxy's static address, so it
      does not depend on Railway's instance IP (redeploy simply reconnects to
      the same proxy).
- [x] **A3. Proxy + sandbox creds round trip.** Ran the 5 test scenarios from
      the Railway shell with `PETPOOJA_PROXY_URL` set; all five saved
      (`PPTEST-0917-12…` → `message="Your order is saved."`), through the
      proxy into the sandbox.
- [x] **A4. Egress confirmed.** Proxy admin saw `TCP_TUNNEL/200 CONNECT
      developerapi.petpooja.com:443` (and the staging execute-api host) in
      the Squid access log while the tests ran.

### Stage B — Whitelist with Petpooja
- [x] **B1.** Static source IP communicated: `35.209.244.171`, already in use
      for all outbound Petpooja traffic.
- [ ] **B2.** Written confirmation the whitelist is active — **came back
      implicitly as part of the Sep 17 handover email ("I have configured the
      endpoints you provided") but not explicitly re-confirmed per-IP.** File
      a one-line ack if prod relay ever 403s before the kitchen terminal.

### Stage C — Go-live (only after B2 AND prod credentials issued)
- [x] **C1.** **Prod credentials issued Sep 17 2026** (outlet `84713`,
      mapping code `c5xeqnhd`; API key/secret/access token in the vendor
      email — live only in Railway Variables + owner's notes, never in the
      repo). Set in Railway:
      - Credentials: `PETPOOJA_APP_KEY`, `PETPOOJA_APP_SECRET`,
        `PETPOOJA_ACCESS_TOKEN`, **`PETPOOJA_REST_ID=c5xeqnhd`** — NOT
        `84713`. This was set to `84713` originally and is the confirmed
        root cause (Petpooja support, Sep 2026) of orders never reaching
        the Online Orders queue/POS terminal despite `save_order` returning
        success — their routing keys off the mapping code, not the numeric
        outlet id. Sandbox's `PETPOOJA_REST_ID=qa3xsbk42g` was already the
        correct alphanumeric-code shape; production just wasn't set to
        match it. See `app/petpooja/config.py`'s module docstring.
      - Endpoints (prod host `pponlineordercb.petpooja.com`, NO `/V1/`):
        `PETPOOJA_SAVE_ORDER_URL=https://pponlineordercb.petpooja.com/save_order`,
        `PETPOOJA_UPDATE_ORDER_STATUS_URL=https://pponlineordercb.petpooja.com/update_order_status`,
        `PETPOOJA_RIDER_STATUS_URL=https://pponlineordercb.petpooja.com/rider_status_update`.
        (`FETCH_MENU_URL` has no prod counterpart; leave unset.)
- [ ] **C1.5 🚨 Squid allowlist the prod host FIRST.** The proxy's acl
      currently allows only `developerapi.petpooja.com` + the staging
      execute-api host — `pponlineordercb.petpooja.com` is NOT there and every
      prod call would 403 with `ProxyError`. On the proxy VM: add
      `acl petpooja dstdomain pponlineordercb.petpooja.com` to the existing
      petpooja acl, then `squid -k parse && systemctl restart squid`. Verify
      next to C3's smoke: proxy log should show
      `TCP_TUNNEL/200 CONNECT pponlineordercb.petpooja.com:443`.
- [ ] **C2.** Ensure `PETPOOJA_PROXY_URL` is exactly the string from Railway
      (verify it wasn't mangled by form entry: re-read it in the Shell:
      `echo "$PETPOOJA_PROXY_URL"`).
- [ ] **C3.** Redeploy; the go-live smoke order = one real path:
      place order → `save_order` through proxy → POS prints → accept →
      callbacks update status. Verify Petpooja's own logs show the whitelisted
      IP as the source for that order.
- [ ] **C4.** Keep the **5-scenario replay** handy for any prod field issues
      (reuse `clientOrderID`s from the whitelisting batch only if you want a
      no-op check; new IDs for real tests — see §4 of PETPOOJA_INTEGRATION.md).

### Stage D — Operations / steady state
- [ ] **D1.** Uptime monitor on `35.209.244.171:3128` (TCP) → Telegram alert
      (see I6). Run from outside, not from the proxy's own lane.
- [ ] **D2.** Put `PETPOOJA_PROXY_URL` in the local `.env` only when you need
      to reproduce prod-from-home; keep `.env.example` empty (done).
- [ ] **D3.** Record the whitelist decision + this doc's date in
      `docs/PETPOOJA_INTEGRATION.md` §3.7 once B2 completes (replace the
      "plan" with "done").

### Stage E — Rollback (how to revert, e.g. if order relay breaks)
- [ ] **E1.** Delete `PETPOOJA_PROXY_URL` from Railway Variables → redeploy.
      `_client()` then uses `None` → direct egress (sandbox works; **prod will
      fail the IP check**, so only use this as an emergency escape or for
      sandbox testing).
- [ ] **E2.** If the breakage was "proxy down", fix/restart the proxy, re-set
      the var, redeploy, and re-run C3.
- [ ] **E3.** The stray sandbox order (I3) needs no cleanup; delete it from the
      dashboard when next touched, for tidiness.

---

## 5. How to verify the wiring on demand (reusable checks)

### Local mock-proxy round trip (no external dependency)
A tiny loopback HTTP proxy + `save_order()` call proves the client honours the
proxy. Key assertion: the mock receives `POST http://target/save_order` —
**absolute-URI form** = proxied; origin-form = direct. Reproduce by running a
mock `socketserver` on an ephemeral port, set `PETPOOJA_PROXY_URL` (any auth
shape incl. `@`) *before* importing `app.petpooja.*`, and assert the request
line. (Test harness from this migration lives in the working notes; re-usable
as `scripts/mock_proxy_check.py` if wanted.)

### Reading the logs
- Success: `Petpooja save_order ok: our order N -> petpooja order M (client order N)`.
- Proxy-down signature: `TOCTOU`/`ConnectTimeout`/`ProxyError` from `httpx` in
  the log, no `save_order ok` line, order still present locally + Telegram ping.

---

## 6. Decisions recorded

| # | Decision | Why |
|---|---|---|
| 1 | Proxy **only** for Petpooja outbound calls; everything else direct | matches Petpooja's IP requirement; minimal blast radius |
| 2 | `PETPOOJA_PROXY_URL` empty ⇒ direct (sandbox-friendly) | integration stays testable without the proxy |
| 3 | Proxy value **not** committed; lives in Railway + local `.env` | it's a basic-auth credential |
| 4 | Whitelist the **observed** egress IP, not the assumed one | A1/A2 before B1; avoids emailing a wrong IP |
| 5 | Fail-fast (timeout → order logged locally, POS ticket missing) until an alert exists | simplest correct behaviour; kitchen still sees the order via Telegram |

## 7. Files touched by this migration
- `app/petpooja/config.py` — added `PETPOOJA_PROXY_URL` (blank default).
- `app/petpooja/client.py` — `_client()` helper; 4 call sites switched to it.
- `.env.example` — added `PETPOOJA_PROXY_URL=` placeholder.
- `docs/PETPOOJA_INTEGRATION.md` — §3.7 states the Railway/static-IP
  requirement this doc operationalises.
- **Pending:** commit of `app/petpooja/` + `.env.example`; this doc.