#!/usr/bin/env python3
"""Local WhatsApp bot REPL — no credentials or webhook needed.

Drives the same conversation logic the webhook uses. Type messages to see
what the bot replies. Start with 'hi'. Simulate WhatsApp actions with
'cart <id>:<qty> ...', 'addr <address>' and 'loc <lat> <lng>'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.whatsapp import conversation, sessions

WA_ID = "919876543210"


def main() -> None:
    db.init_db()
    db.seeded()
    sessions.init_sessions()
    sessions.reset(WA_ID)
    print("Tulsi Foods WhatsApp bot REPL (wa_id:", WA_ID, ") — type messages, Ctrl+D to exit.\n")
    while True:
        try:
            line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line.strip():
            continue
        kw = {}
        if line.startswith("loc "):  # "loc 13.03 80.26" = share a location pin
            _, lat, lng = line.split()
            kw = {"lat": lat, "lng": lng}
        elif line.startswith("cart "):  # "cart mini-thali:2 masala-chai" = catalogue cart
            kw = {"catalog_items": [{"id": p.split(":")[0], "qty": int((p.split(":") + ["1"])[1])}
                                    for p in line.split()[1:]]}
        elif line.startswith("addr "):  # "addr 12 Luz Church Road, 600004" = address form
            kw = {"address": {"address": line[5:]}}
        for reply in conversation.handle(WA_ID, line, "Test Customer", **kw):
            print(f"bot [{reply['type']}]> {reply.get('text', reply.get('header', ''))}")
            for b in reply.get("buttons", []):
                print("      button:", b)
            for sec in reply.get("sections", []):
                for row in sec.get("rows", []):
                    print("      row:", row["id"], "-", row["title"])
                if sec.get("ids"):
                    print("      products:", ", ".join(sec["ids"]))
            if reply.get("url"):
                print("      link:", reply["label"], reply["url"])


if __name__ == "__main__":
    main()
