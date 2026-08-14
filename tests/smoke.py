"""End-to-end smoke test: boots the app in-process, exercises the full flow."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

PORT = os.environ.get("TULSI_TEST_PORT", "8000")
BASE = f"http://127.0.0.1:{PORT}"
TOKEN = "tulsi"


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")
    if not cond:
        raise SystemExit(1)


def main():
    print("smoke test")
    with httpx.Client(base_url=BASE, timeout=10) as c:
        r = c.get("/")
        check("GET / renders", r.status_code == 200 and b"Tulsi Foods" in r.content, r.status_code)

        r = c.get("/admin")
        check("GET /admin renders", r.status_code == 200 and b"Today" in r.content, r.status_code)

        r = c.get("/privacy-policy")
        check("GET /privacy-policy renders", r.status_code == 200 and b"Privacy Policy" in r.content, r.status_code)

        r = c.get("/api/menu")
        data = r.json()
        check("menu has 10 groups", len(data["groups"]) == 10, len(data["groups"]))
        total = sum(len(g["items"]) for g in data["groups"])
        check("menu has 140 items", total == 140, total)
        thali = next(it for g in data["groups"] if g["group"] == "Thalis & Combos"
                     for it in g["items"] if it["name"] == "North Indian Thali")
        check("thali price from data", thali["price"] == 248, thali["price"])

        # availability: start with 2 items unavailable
        ids = [it["id"] for g in data["groups"] for it in g["items"]]
        off = ids[:2]
        r = c.post("/api/admin/availability", json={"available_ids": ids[2:], "unavailable_ids": off},
                   headers={"X-Admin-Token": TOKEN})
        check("set availability", r.status_code == 200)

        r = c.get("/api/menu")
        flags = {(it["id"]): it["available"] for g in r.json()["groups"] for it in g["items"]}
        check("availability reflected in menu", not flags[off[0]] and flags[ids[2]])

        # admin auth
        r = c.post("/api/admin/availability", json={"available_ids": ids, "unavailable_ids": []})
        check("admin without token rejected", r.status_code == 401)

        # delivery fee
        r = c.get("/api/delivery", params={"km": 2})
        check("zone A fee", r.json()["fee"] == 30)
        r = c.get("/api/delivery", params={"km": 6})
        check("zone C fee", r.json()["fee"] == 70)
        r = c.get("/api/delivery", params={"km": 9})
        check("outside zone", r.json()["fee"] is None)

        # order: one available item, delivery, low subtotal -> min order error
        payload = {
            "name": "Test", "phone": "9876543210", "order_type": "delivery",
            "km": 2, "payment_method": "cod",
            "items": [{"item_id": ids[3], "qty": 1}],
        }
        r = c.post("/api/orders", json=payload)
        check("min order enforced", r.status_code == 400, r.json())

        # order: unavailable item -> 409
        payload["items"] = [{"item_id": off[0], "qty": 1}]
        payload["items"][0]["qty"] = 3  # push subtotal over min
        r = c.post("/api/orders", json=payload)
        check("unavailable item rejected", r.status_code == 409, r.json())

        # order: good order
        payload["items"] = [{"item_id": ids[3], "qty": 2}]
        r = c.post("/api/orders", json=payload)
        check("order created", r.status_code == 200, r.json())
        oid = r.json()["order_id"]

        r = c.get(f"/api/orders/{oid}")
        check("order retrievable", r.status_code == 200 and r.json()["status"] == "new")
        check("order total correct", abs(r.json()["total"] - (r.json()["subtotal"] + r.json()["delivery_fee"])) < 0.01)

        r = c.get("/api/orders")
        check("order list has the order", any(o["id"] == oid for o in r.json()["orders"]))

        # repeat yesterday on fresh day
        r = c.post("/api/admin/availability/repeat-yesterday", headers={"X-Admin-Token": TOKEN})
        check("repeat-yesterday", r.status_code in (200, 400), r.json())

    print("whatsapp webhook")
    with httpx.Client(base_url=BASE, timeout=10) as c:
        r = c.get("/webhook/whatsapp", params={
            "hub.mode": "subscribe", "hub.verify_token": "tulsi_verify", "hub.challenge": "12345"})
        check("webhook verify ok", r.status_code == 200 and r.text == "12345", r.status_code)
        r = c.get("/webhook/whatsapp", params={
            "hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "12345"})
        check("webhook bad token", r.status_code == 403)
        payload = {
            "entry": [{"changes": [{"value": {
                "contacts": [{"profile": {"name": "Bot"}}],
                "messages": [{"from": "919888888888", "type": "text", "text": {"body": "MENU"}}],
            }}]}],
        }
        r = c.post("/webhook/whatsapp", json=payload)
        check("webhook message accepted", r.status_code == 200, r.status_code)

        # human takeover: mom replies from the Business app -> echo webhook
        echo = {
            "entry": [{"changes": [{"value": {
                "smb_message_echoes": [{
                    "id": "919888888888",
                    "messages": [{"from": "999888777666", "to": "919888888888",
                                  "type": "text", "id": "echo-1"}],
                }],
            }}]}],
        }
        r = c.post("/webhook/whatsapp", json=echo)
        check("echo accepted", r.status_code == 200, r.status_code)

        r = c.get("/api/admin/conversations", headers={"X-Admin-Token": TOKEN})
        conv = next((x for x in r.json()["conversations"] if x["wa_id"] == "919888888888"), None)
        check("echo marks chat human", conv is not None and conv["human"] is True, conv)

        # after takeover the bot must not reply to that customer
        log_path = Path(__file__).resolve().parent.parent / "data" / "whatsapp.log"
        log_before = log_path.read_text()
        r = c.post("/webhook/whatsapp", json=payload)
        check("message while human-owned accepted", r.status_code == 200, r.status_code)
        log_after = log_path.read_text()
        check("bot silent after takeover", log_after == log_before, log_after[-200:])

        # admin can switch back to Bot
        r = c.post("/api/admin/conversations/919888888888/human",
                   json={"human": False}, headers={"X-Admin-Token": TOKEN})
        check("toggle back to bot", r.status_code == 200 and r.json()["human"] is False, r.json())
        r = c.post("/webhook/whatsapp", json=payload)
        check("message after toggle accepted", r.status_code == 200, r.status_code)
        check("bot replies again", log_path.read_text() != log_after, "")

    print("whatsapp conversation flow")
    from app import db
    from app.whatsapp import conversation, sessions

    db.init_db()
    db.seeded()
    sessions.init_sessions()
    sessions.reset("919999999999")
    WID = "919999999999"

    def send(msg):
        return conversation.handle(WID, msg, "Bot Test")

    out = send("MENU")
    check("welcome shown", any("Tulsi Foods" in m["text"] for m in out))
    out = send("1")
    check("category items", any("Thalis & Combos" in m["text"] for m in out))
    out = send("4")  # Mini Thali ₹188 — over nothing yet
    check("item added", any("Mini Thali" in m["text"] for m in out))
    out = send("3")  # Executive Combo ₹281
    check("item added", any("Executive Combo" in m["text"] for m in out))
    out = send("CART")
    check("cart shows 2 lines", any("Subtotal: ₹469" in m["text"] for m in out))
    out = send("CHECKOUT")
    check("asks name", any("name" in m["text"] for m in out))
    send("Bot Test")
    send("D")
    send("12, Mylapore")
    send("1")
    send("NOW")
    send("UPI")
    out = send("YES")
    check("order confirmed", any("confirmed" in m["text"] for m in out), out)
    out = send("STATUS")
    check("status", any("placed" in m["text"] for m in out))
    out = send("REORDER")
    check("reorder prompt", any("Reorder" in m["text"] for m in out))
    out = send("YES")
    check("reorder placed", any("Order #" in m["text"] for m in out), out)

    print("ALL PASS")


if __name__ == "__main__":
    main()
