# Tulsi Foods — Direct Ordering Platform

Move Tulsi Foods (Mylapore, Chennai; pure-veg family restaurant) off Swiggy/Zomato
(~27–32% of every order goes to aggregators) onto direct ordering: a WhatsApp bot +
mobile-first web app, backed by the same FastAPI service.

## Stack

- Python 3.12 + FastAPI + SQLite (single file, no DB server to babysit)
- Server-rendered Jinja2 web UI (works without JavaScript except checkout totals)
- WhatsApp Cloud API (Graph API v23.0) via `httpx`
- `python-dotenv` for local `.env`; deployed on Railway via Dockerfile

## Live URLs

- **Web ordering + admin:** https://api.tulsifoods.app
- **Webhook:** https://api.tulsifoods.app/webhook/whatsapp
- **GitHub (private):** https://github.com/rahullath/tulsi-foods
- **Domain:** tulsifoods.app (name.com) — root still unconnected; Wix wanted money to
  connect it, so the landing page will be designed manually (see "Landing page").

## Project layout

```
app/
  main.py              FastAPI app: web routes, admin API, mounts webhook router
  config.py            zones, WhatsApp env vars; loads .env via python-dotenv
  db.py                SQLite schema + helpers (customers, orders, order_items, availability)
  menu.py              menu.json loader, groups, popularity, availability helpers
  orders.py            shared order service (web + bot): build_lines, delivery_quote/fee, create_order
  webhooks.py          WhatsApp webhook: GET verify handshake, POST messages, HMAC signature check
  whatsapp/
    conversation.py    bot state machine (pure logic, no network)
    client.py          Graph API send_text/send_buttons/send_outbound; dry-run log mode
    sessions.py        per-customer conversation state in SQLite (wa_sessions)
  templates/           base.html, index.html (ordering), admin.html (menu/orders)
  static/              style.css, app.js, admin.js
data/
  menu.json            140 items / 10 groups / 49 popular (prices are APPROXIMATE)
  tulsi.db             SQLite DB (created on startup; gitignored)
  whatsapp.log         dry-run outbound log (dev mode only)
scripts/
  build_menu.py        regenerate data/menu.json from the Swiggy CSVs
  whatsapp_repl.py     local bot REPL (no credentials/webhook needed)
tests/
  smoke.py             full E2E: web + admin + webhook + bot conversation (37 checks)
Dockerfile + docker-entrypoint.sh   deploy image (volume-safe menu seeding)
.env                    secrets — NEVER commit (gitignored)
```

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in WhatsApp creds
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Without WhatsApp credentials the bot runs in **dry-run mode**: replies are appended to
`data/whatsapp.log` instead of being sent.

### Bot REPL

```bash
.venv/bin/python scripts/whatsapp_repl.py
```

Drives the same conversation logic the webhook uses — test the whole order flow locally.

### Tests

```bash
.venv/bin/python - <<'EOF'
import subprocess, sys, time, socket, os
port = 8010
p = subprocess.Popen([".venv/bin/uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
try:
    for _ in range(100):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.2); s.close(); break
        except OSError: time.sleep(0.2)
    sys.exit(subprocess.run([".venv/bin/python", "tests/smoke.py"],
                            env=dict(os.environ, TULSI_TEST_PORT=str(port))).returncode)
finally:
    p.terminate(); p.wait(timeout=5)
EOF
```

## Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `WHATSAPP_TOKEN` | (empty) | Graph API access token. Empty → dry-run mode. |
| `WHATSAPP_PHONE_ID` | (empty) | Meta Cloud API phone number ID. |
| `WHATSAPP_VERIFY_TOKEN` | `tulsi_verify` | Must match Meta webhook verify token. |
| `WHATSAPP_APP_SECRET` | (empty) | If set, webhook POSTs must carry a valid `X-Hub-Signature-256`. |
| `TULSI_ADMIN_TOKEN` | `tulsi` | `/admin` access. Change before going live. |
| `WHATSAPP_DRY_LOG` | `data/whatsapp.log` | Dry-run outbound log path. |

Set the same variables in Railway (Variables tab) in production.

## WhatsApp webhook

- `GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<t>&hub.challenge=<n>` → returns `<n>`.
  This is the handshake Meta runs on **Verify and save**.
- `POST /webhook/whatsapp` → parses inbound messages (text + interactive button replies),
  runs the conversation state machine, replies via the Graph API. Returns 200 fast so Meta
  doesn't retry. Optional HMAC signature verification when `WHATSAPP_APP_SECRET` is set.

Meta Dashboard → WhatsApp → Configuration → Webhook:
- Callback URL: `https://api.tulsifoods.app/webhook/whatsapp`
- Verify token: `tulsi_verify`
- Subscribe to field: **`messages`** (only one needed).

## Bot commands (customer-facing)

`MENU`, category/item numbers (e.g. `3` or `3 x2`), `BACK` (0 = next page),
`CART`, `REMOVE <n>`, `CLEAR`, `CHECKOUT` (name → delivery/pickup → address → distance →
when → payment → confirm), `STATUS`, `REORDER` (repeat last order), `HELP`, `YES`/`EDIT`/`CANCEL`,
and a one-time "add a Masala Chai?" nudge on the first item.

## Delivery rules (from spec §7, real distance data)

| Zone | Distance | Fee | Min order |
|---|---|---|---|
| A (core) | ≤3 km | ₹30 | ₹250 |
| B | 3–5 km | ₹50 | ₹300 |
| C | 5–7 km | ₹70 | ₹350 |
| — | >7 km | not served | — |

Free delivery above ₹700. **No order flow for desserts; pre-order is a theme, never a block.**

## Deployment

- **Host:** Railway (railway.app), Dockerfile build, stays up 24/7 (webhooks need an
  always-on server; Render's free tier sleeps).
- **Persistence:** Railway volume mounted at `/app/data` (SQLite). `docker-entrypoint.sh`
  seeds `menu.json` into the volume on first boot.
- **DNS:** `api.tulsifoods.app` → CNAME to the Railway target. Root `tulsifoods.app` is
  still for the landing page.
- **Deploy flow:** push to `master` → Railway auto-deploys.

## Current status / next steps

- [x] Data analysis + spec v2 (backup: `spec.v1.bak.md`)
- [x] Web ordering + admin + availability (37/37 smoke checks)
- [x] WhatsApp bot (menu → cart → checkout → order → status → reorder), webhook wired
- [x] Live on Railway at api.tulsifoods.app; Meta webhook connected (test phase)
- [ ] **Production WhatsApp switch** (tomorrow, mom must be awake for the OTP):
      1. Permanent system-user token (test token expires ~24h)
      2. Business verification (start early — can take days)
      3. Add real phone number + OTP + display name approval + 2-step PIN
      4. Add billing (Meta charges per conversation after free tier)
- [ ] **Landing page** — Wix wanted money to connect the domain; design manually instead.
      Prompts/plan captured in chat. Add WhatsApp button
      `https://wa.me/91<number>?text=Hi%20Tulsi` + link to api.tulsifoods.app.
- [ ] **Petpooja integration** (spec's first integration task) + menu price confirmation
      (current prices are averages from Swiggy revenue/qty, not the POS).
- [ ] Delivery tool decision (who actually delivers; spec discusses logistics partners)
- [ ] Change `TULSI_ADMIN_TOKEN` before go-live
- [ ] Lost file `1786536197478.csv` (order timings, → `09_swiggy_order_timings_jul2026.csv`)
      needs re-download from Swiggy portal if wanted

## Known notes / gotchas

- Jinja2: `g["items"]`, never `g.items` (dict method shadowing).
- Keep 1 uvicorn worker — SQLite isn't multi-writer friendly.
- `REORDER` falls back to a hardcoded 2.0 km for delivery orders lacking distance data.
- Backgrounding uvicorn with `&` in the bash tool hangs it — use the subprocess test pattern.
