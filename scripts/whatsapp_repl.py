#!/usr/bin/env python3
"""Local WhatsApp bot REPL — no credentials or webhook needed.

Drives the same conversation logic the webhook uses. Type messages to see
what the bot replies. Start with 'hi' or 'MENU'.
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
        for reply in conversation.handle(WA_ID, line, "Test Customer"):
            kind = "buttons" if reply["type"] == "buttons" else "text"
            print(f"bot [{kind}]> {reply['text']}")
            if reply.get("buttons"):
                print("      buttons:", " | ".join(reply["buttons"]))


if __name__ == "__main__":
    main()
