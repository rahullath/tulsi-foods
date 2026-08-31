#!/usr/bin/env python3
"""Enrich data/menu.json with Petpooja's own item export.

Run AFTER build_menu.py (which derives menu.json from Swiggy sales data —
that source has no descriptions and misses items Swiggy barely sold, like a
newly-added dish). This script layers Petpooja's real item list on top:

  - description: pulled in wherever Petpooja has one for a matched item.
  - new items: present in Petpooja but missing from menu.json (matched by
    name) get added using Petpooja's own list price.
  - half_price: Sabzi-category items get a default half-portion price at
    60% of full, rounded to the nearest ₹10 — a placeholder estimate, NOT
    Petpooja/mom-confirmed pricing. Flagged in _meta; override in
    data/menu.json directly (this script won't clobber an existing value on
    re-run) once real half prices are set.

Inputs (gitignored, re-export from Petpooja's admin panel when refreshing):
  data/petpooja_items.csv
  data/petpooja_addons.csv  (read but only reported on for now — see
                              docs/HANDOFF.md for why addon-group -> our
                              checkout isn't wired up yet)

Idempotent: safe to re-run after re-exporting Petpooja's CSV or rebuilding
from Swiggy data.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MENU_FILE = DATA / "menu.json"
ITEMS_CSV = DATA / "petpooja_items.csv"
ADDONS_CSV = DATA / "petpooja_addons.csv"

HALF_ELIGIBLE_CATEGORY = "Sabzi"
HALF_PRICE_RATIO = 0.6  # placeholder — confirm real half prices with mom


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "item"


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def round_to_10(v: float) -> int:
    return int(round(v / 10.0)) * 10


def load_petpooja_items() -> list[dict]:
    with open(ITEMS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("Name", "").strip()]


def main() -> None:
    menu = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    items = menu["items"]
    by_norm_name = {normalize(it["name"]): it for it in items}

    pp_items = load_petpooja_items()

    matched, added, unmatched = 0, 0, []
    for row in pp_items:
        name = row["Name"].strip()
        online_name = (row.get("Online_Name") or "").strip() or name
        desc = (row.get("Description") or "").strip()
        category = (row.get("Category") or "").strip()
        try:
            price = round(float(row["Price"])) if row.get("Price") else None
        except ValueError:
            price = None

        key = normalize(online_name)
        existing = by_norm_name.get(key) or by_norm_name.get(normalize(name))

        if existing:
            matched += 1
            if desc and not existing.get("description"):
                existing["description"] = desc
        else:
            unmatched.append((name, category, price))

    # Known addition confirmed with the user: Fruit Chaat exists in Petpooja
    # but wasn't in the Swiggy-derived menu (low/no Swiggy sales history).
    for name, category, price in list(unmatched):
        if normalize(name) == normalize("Fruit Chaat") and price:
            src = next(r for r in pp_items if r["Name"].strip() == name)
            new_item = {
                "id": slugify(name),
                "name": name,
                "category": category or "Chaats",
                "group": "Chaats & Snacks",
                "price": price,
                "avg_price": price,
                "popular": False,
                "description": (src.get("Description") or "").strip(),
            }
            items.append(new_item)
            by_norm_name[normalize(name)] = new_item
            unmatched.remove((name, category, price))
            added += 1

    half_priced = 0
    for it in items:
        if it.get("category") == HALF_ELIGIBLE_CATEGORY and "half_price" not in it:
            it["half_price"] = round_to_10(it["price"] * HALF_PRICE_RATIO)
            half_priced += 1

    menu.setdefault("_meta", {})["petpooja_merge"] = {
        "source": str(ITEMS_CSV.relative_to(ROOT)),
        "matched": matched,
        "added": added,
        "half_price_ratio": HALF_PRICE_RATIO,
        "half_priced_items": half_priced,
        "note": (
            "half_price values are a 60%-of-full placeholder, not confirmed "
            "with the restaurant — override per item in menu.json once real "
            "half-portion prices are set."
        ),
    }

    MENU_FILE.write_text(json.dumps(menu, indent=2, ensure_ascii=False))

    print(f"Matched {matched} items, added {added} new item(s), set half_price on {half_priced} Sabzi item(s).")
    if unmatched:
        print(f"\n{len(unmatched)} Petpooja item(s) not found in menu.json (not auto-added, review manually):")
        for name, category, price in unmatched:
            print(f"  {name!r:40s} {category:20s} price={price}")


if __name__ == "__main__":
    sys.exit(main())
