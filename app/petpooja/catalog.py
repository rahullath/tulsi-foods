"""Reconcile our menu item slugs (data/menu.json) to Petpooja's real catalog
item ids — the fix for KNOWN GAP §3.2 documented in app/petpooja/mapping.py.

Source of truth: DATA_DIR/petpooja_menu_raw.json, written whenever the
inbound Push Menu webhook (app/webhooks.py, petpooja_push_menu) gets a fresh
push from the Petpooja POS/dashboard ("Menu Trigger", restID 84713). Each
item in that payload carries its real `itemid` (a string), and the addon
groups carry `addongroupid`/`addonitemid`.

Before this module, Save Order sent our own slug as OrderItem.id (e.g.
"north-indian-thali"). Petpooja accepts the call (success=1) but the item id
doesn't exist in the catalog, so the order was invisible / mis-attributed on
the POS and the Online Orders dashboard. This module resolves each slug to
the real catalog id by matching *our* item name (from data/menu.json) against
the pushed `itemname`, then falls back to the slug with a loud log line so a
missing menu item never silently breaks an order.

Notes on matching:
- Match key is the normalized name only (lowercased, non-alphanumerics
  stripped): "Chola Bhatura" in both sources hits. Price is deliberately NOT
  part of the key — menu.json prices are Swiggy platform averages, not the
  Petpooja catalogue's.
- Half portions (<id>__half) resolve to the base item's itemid when the POS
  has no separate " (Half)" entry — the receipt still shows the "(Half)"
  name and half price, both sent through in the Save Order payload.
- Tax: the catalogue marks its items `tax_inclusive: true` and the pushed
  tax rates are CGST 2.5% + SGST 2.5% = 5%, matching our GST_RATE. The Save
  Order payload's per-item `tax_inclusive` now mirrors the catalogue's own
  flag (see map_order_items) instead of hardcoding False, so the POS doesn't
  re-materialize GST on top of the exact total the customer already paid.
  The item price we send stays our checkout price and the CGST/SGST lines
  still reflect the GST the customer actually paid — flag mirrored, money
  unchanged. (True dollar-for-euro alignment would mean sourcing item prices
  from the catalogue too — a menu-sync follow-up, since data/menu.json
  prices are flagged as "approximate platform averages".)
"""
import json
import logging
import re
import sys

from ..config import DATA_DIR
from ..menu import HALF_SUFFIX, _base_id, get_item

log = logging.getLogger("petpooja.catalog")

CACHE_FILE = DATA_DIR / "petpooja_menu_raw.json"

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm(name: str) -> str:
    return _NON_ALNUM.sub("", (name or "").lower())


class Catalog:
    """Snapshot of the pushed menu, built once per request.

    Re-reading a ~tens-of-kB file per order is cheap and keeps every order
    using the latest push, so no long-lived cache is kept.
    """

    def __init__(self, raw: dict):
        self._by_name: dict[str, dict] = {}
        self._addon_by_name: dict[str, str] = {}
        for it in raw.get("items") or []:
            n = _norm(it.get("itemname", ""))
            if not n:
                continue
            existing = self._by_name.get(n)
            # Prefer the entry that's active over a same-named inactive one
            # (e.g. a catalog keeping both an old and new item under one name).
            if existing is None or (existing.get("active") != 1 and it.get("active") == 1):
                self._by_name[n] = it
        for group in raw.get("addongroups") or []:
            for a in group.get("addongroupitems") or []:
                an = _norm(a.get("addonitem_name", ""))
                if an and an not in self._addon_by_name:
                    self._addon_by_name[an] = str(a.get("addonitemid") or "")

    def item_by_name(self, name: str) -> dict | None:
        return self._by_name.get(_norm(name))

    def addon_item_id(self, addon_name: str) -> str | None:
        return self._addon_by_name.get(_norm(addon_name))

    def item_tax_inclusive(self, name: str) -> bool:
        rec = self.item_by_name(name)
        return bool(rec and rec.get("tax_inclusive"))

    def _match(self, menu_item_id: str) -> tuple[dict | None, dict | None]:
        """Return the (catalog record, menu item) for a slug.

        Falls back to the base item for "<id>__half" slugs (the POS has no
        separate " (Half)" entry — half portions share the base item's id,
        name flag, and tax treatment). (None, None) when the slug is unknown.
        """
        m = get_item(menu_item_id)
        if not m:
            return None, None
        rec = self.item_by_name(m["name"])
        if rec is not None:
            return rec, m
        if menu_item_id.endswith(HALF_SUFFIX):
            base = get_item(_base_id(menu_item_id))
            if base:
                rec = self.item_by_name(base["name"])
                if rec is not None:
                    return rec, m
        return None, m

    def resolve(self, menu_item_id: str) -> str:
        """Map a data/menu.json slug to Petpooja's real `itemid`.

        Returns the slug unchanged when unmappable so callers keep working
        (with a logged warning) instead of dropping the line.
        """
        rec, m = self._match(menu_item_id)
        if rec is None:
            if m is not None:
                log.warning("Petpooja catalog: no itemid for '%s' (%s); falling back to slug",
                            m["name"], menu_item_id)
            return menu_item_id
        if rec.get("active") == 0:
            log.warning("Petpooja catalog: '%s' (%s) maps to inactive itemid %s",
                        m["name"], menu_item_id, rec.get("itemid"))
        return str(rec.get("itemid") or menu_item_id)


def _catalog() -> "Catalog | None":
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        log.exception("Petpooja catalog: could not read %s", CACHE_FILE)
        return None
    return Catalog(raw)


def petpooja_item_id(menu_item_id: str) -> str:
    """1-item convenience wrapper around Catalog.resolve()."""
    c = _catalog()
    return c.resolve(menu_item_id) if c else menu_item_id


def map_order_items(order_items: list[dict]) -> list[dict]:
    """Annotate each order item with ``petpooja_item_id`` (real catalog id)
    and ``petpooja_tax_inclusive`` (the catalog's own tax flag for that item).

    ``order_items`` follows app.db.get_order()'s shape ({item_id, name,
    price, qty}); copies get the new keys alongside the original slug.
    Unmapped items keep the slug and default to tax_exclusive — same
    behaviour as before §3.2 landed, so a missing catalog item can't
    silently change how an order is taxed.
    """
    c = _catalog()
    out = []
    for it in order_items:
        o = dict(it)
        rec, _ = c._match(o["item_id"]) if c else (None, None)
        o["petpooja_item_id"] = str(rec.get("itemid") or o["item_id"]) if rec else str(o["item_id"])
        o["petpooja_tax_inclusive"] = bool(rec and rec.get("tax_inclusive"))
        out.append(o)
    return out


# ---------------------------------------------------------------- reporting

def _coverage_report() -> None:
    """Compare every data/menu.json item against the pushed catalogue.

    Prints matched/unmatched counts and lists so we can spot menu.json items
    Petpooja's catalogue doesn't know (to prune or to fix on the POS). No
    cache file yet prints a plain hint. Exits non-zero on any miss.
    """
    from .. import menu as menu_mod

    items = [m for m in menu_mod.load_menu() if not m["id"].endswith(HALF_SUFFIX)]
    c = _catalog()
    if c is None:
        print(f"no cache file at {CACHE_FILE} — trigger Menu Push from the POS "
              "dashboard first (or copy the pushed payload here).")
        sys.exit(2)
    if not c._by_name:
        print(f"{CACHE_FILE} has no items ({CACHE_FILE.stat().st_size} bytes) — "
              "this is likely the stale placeholder; restore the real pushed "
              "payload before running the coverage check.")
        sys.exit(2)

    matched, unmatched = [], []
    for m in items:
        (matched if c.item_by_name(m["name"]) else unmatched).append(m)
    print(f"menu.json sellable items: {len(items)}")
    print(f"  matched in Petpooja catalogue: {len(matched)}")
    print(f"  NOT found: {len(unmatched)}")
    for m in sorted(unmatched, key=lambda x: x["name"]):
        print(f"  - {m['name']}  ({m['id']})")
    sys.exit(1 if unmatched else 0)


def _self_test() -> None:
    """Sanity-check resolution against a synthetic sample of the pushed shape."""
    sample = {
        "items": [
            {"itemid": "1250363094", "itemname": "North Indian Thali",
             "itemallowaddon": "N", "active": 1, "tax_inclusive": True},
            {"itemid": "1277216995", "itemname": "Rajasthani Thali",
             "active": 0, "tax_inclusive": True},
            {"itemid": "1250363095", "itemname": "Mini Thali",
             "addon": [{"addon_group_id": "553159"}], "active": 1},
            {"itemid": "666", "itemname": "Chola Bhatura (Full)", "active": 1},
        ],
        "addongroups": [
            {"addongroupid": "553159", "addongroupname": "Add Ons", "addongroupitems": [
                {"addonitemid": "13652618", "addonitem_name": "Pepsi (300 Ml)",
                 "addonitem_price": 70}]},
        ],
    }
    c = Catalog(sample)
    assert c.resolve("north-indian-thali") == "1250363094"
    assert c.resolve("rajasthani-thali") == "1277216995"
    assert c.addon_item_id("Pepsi (300 Ml)") == "13652618"
    assert c.item_tax_inclusive("North Indian Thali") is True
    assert c.resolve("no-such-slug") == "no-such-slug"
    assert c.resolve("half") == "half"  # get_item("half") is None
    mod = sys.modules[__name__]
    orig = mod._catalog
    mod._catalog = lambda: c
    try:
        mapped = mod.map_order_items([{"item_id": "north-indian-thali",
                                       "name": "North Indian Thali",
                                       "price": 248, "qty": 1},
                                      {"item_id": "totally-unknown-dish",
                                       "name": "totally-unknown-dish",
                                       "price": 10, "qty": 1}])
    finally:
        mod._catalog = orig
    assert mapped[0]["petpooja_item_id"] == "1250363094"
    assert mapped[0]["petpooja_tax_inclusive"] is True
    assert mapped[1]["petpooja_item_id"] == "totally-unknown-dish"
    assert mapped[1]["petpooja_tax_inclusive"] is False
    print("catalog self-test OK")
    sys.exit(0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    if "--self-test" in sys.argv:
        _self_test()
    else:
        _coverage_report()