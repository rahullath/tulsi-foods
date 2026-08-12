"""Menu catalogue loaded from data/menu.json + per-day availability."""
import json
from datetime import date
from functools import lru_cache

from .config import MENU_FILE
from . import db


@lru_cache(maxsize=1)
def load_menu() -> list[dict]:
    data = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {m["id"]: m for m in items}
    return items


def get_item(item_id: str) -> dict | None:
    for m in load_menu():
        if m["id"] == item_id:
            return m
    return None


def is_available(item_id: str, day: str | None = None) -> bool:
    day = today(day)
    available = db.get_available_ids(day)
    if not available:
        return True  # no availability saved yet → everything available
    return item_id in available


def today(day: str | None = None) -> str:
    return day or date.today().isoformat()


def menu_for(day: str | None = None) -> list[dict]:
    """Full menu with today's availability flag."""
    day = today(day)
    available = db.get_available_ids(day)
    out = []
    for m in load_menu():
        row = dict(m)
        row["available"] = m["id"] in available if available else True
        out.append(row)
    return out


def grouped(day: str | None = None) -> list[dict]:
    """Menu grouped by display group, available-first within each group."""
    items = menu_for(day)
    groups: dict[str, list[dict]] = {}
    order = []
    for m in items:
        g = m["group"]
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append(m)
    for g in order:
        groups[g].sort(key=lambda x: (not x["available"], not x["popular"], x["name"]))
    return [{"group": g, "items": groups[g]} for g in order]
