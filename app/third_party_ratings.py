"""Swiggy's per-dish ratings, shown on our dish pages as Swiggy's ratings.

Display only, never structured data: Google's review-snippet guidelines say
"Don't aggregate reviews or ratings from other websites", so these stay out
of the Product JSON-LD (which carries only our own verified ratings, see
db.dish_rating). Refresh app/swiggy_ratings.json from the Swiggy menu page
now and then; ratings below SHOW_MIN or with too few votes aren't shown.
"""
import json
from functools import lru_cache
from pathlib import Path

FILE = Path(__file__).resolve().parent / "swiggy_ratings.json"  # in the image, not on the data volume
SHOW_MIN = 4.0
MIN_COUNT = 5


@lru_cache(maxsize=1)
def _data() -> dict:
    try:
        return json.loads(FILE.read_text())
    except (OSError, ValueError):
        return {"items": {}}


def swiggy(item_id: str) -> dict | None:
    """{'rating', 'count', 'count_text', 'url', 'as_of'} worth showing, or None."""
    d = _data()
    r = d.get("items", {}).get(item_id.split("__")[0])
    if not r or r["rating"] < SHOW_MIN or r["count"] < MIN_COUNT:
        return None
    n = r["count"]
    count_text = f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k+" if n >= 1000 else str(n)
    return {"rating": r["rating"], "count": n, "count_text": count_text,
            "url": d.get("url"), "as_of": d.get("as_of")}


def restaurant() -> dict | None:
    return _data().get("restaurant")
