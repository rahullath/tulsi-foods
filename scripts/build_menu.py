#!/usr/bin/env python3
"""Build the menu dataset from the Swiggy item CSVs.

Primary source: 08_highest_selling_items_jun-aug2026.csv
(140 items, real categories, prices derived from revenue/qty).
Prices are APPROXIMATE (platform averages incl. discounts) and must be
confirmed against Petpooja before going live.

Output: data/menu.json
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "08_highest_selling_items_jun-aug2026.csv"

DISPLAY_GROUPS = [
    ("Thalis & Combos", {"Thalis", "Executive Combo", "Rice Bowl"}),
    ("Parathas & Breads", {"Indian Breads"}),
    ("Chaats & Snacks", {"Chaats", "Papads", "Sandwiches"}),
    ("Starters", {"Starters"}),
    ("Soups & Rice", {"Soups", "Rice"}),
    ("Sabzi", {"Sabzi"}),
    ("Italian", {"Italian"}),
    ("Chai & Beverages", {"Beverages", "Juices", "Milkshake", "Thirst Quenchers"}),
    ("Desserts", {"Desserts"}),
    ("Specialities", {"Specialities"}),
]

GROUP_ORDER = [g for g, _ in DISPLAY_GROUPS]


def group_of(category: str) -> str:
    for name, cats in DISPLAY_GROUPS:
        if category in cats:
            return name
    return "Other"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "item"


def round_price(v: float) -> int:
    return int(round(v))


def main() -> None:
    rows = list(csv.reader(open(SRC, newline="")))
    hdr = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Item")
    raw = []
    for r in rows[hdr + 1:]:
        if len(r) < 4 or not r[0].strip():
            continue
        if r[0].strip() in ("Total", "Min.", "Max.", "Avg."):
            continue
        try:
            qty = float(r[2])
            revenue = float(r[3])
        except ValueError:
            continue
        raw.append({"name": r[0].strip(), "category": r[1].strip(), "qty": qty, "revenue": revenue})

    # revenue-ranked popularity cut: items that make up ~80% of revenue
    raw.sort(key=lambda x: -x["revenue"])
    total = sum(x["revenue"] for x in raw)
    acc, popular = 0.0, set()
    for x in raw:
        popular.add(x["name"])
        acc += x["revenue"]
        if acc >= total * 0.8:
            break

    menu = []
    for x in raw:
        avg = x["revenue"] / x["qty"] if x["qty"] else 0
        menu.append({
            "id": slugify(x["name"]),
            "name": x["name"],
            "category": x["category"],
            "group": group_of(x["category"]),
            "price": round_price(avg),
            "avg_price": round(avg, 2),
            "popular": x["name"] in popular,
            "qty_2mo": round(x["qty"], 1),
            "revenue_2mo": round(x["revenue"], 2),
        })

    # stable: popular first, then by revenue desc within group
    menu.sort(key=lambda x: (not x["popular"], -x["revenue_2mo"]))

    DATA.mkdir(exist_ok=True)
    out = {
        "_meta": {
            "source": str(SRC),
            "built_from": "08_highest_selling_items_jun-aug2026.csv",
            "note": "Prices are approximate platform averages. Confirm against Petpooja.",
            "item_count": len(menu),
            "popular_count": len(popular),
        },
        "display_groups": GROUP_ORDER,
        "items": menu,
    }
    (DATA / "menu.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"Built data/menu.json: {len(menu)} items, {len(popular)} popular (≥80% revenue).")
    by_group = defaultdict(int)
    for m in menu:
        by_group[m["group"]] += 1
    for g in GROUP_ORDER:
        print(f"  {g}: {by_group.get(g, 0)} items")
    print("\nPopular items:")
    for m in menu:
        if m["popular"]:
            print(f"  {m['name'][:42]:44s} ₹{m['price']:>4}  {m['group']}")


if __name__ == "__main__":
    sys.exit(main())
