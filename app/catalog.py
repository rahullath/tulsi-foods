"""WhatsApp/Meta product catalog feed, generated from data/menu.json on request.

Mirrors Meta's official sample catalog_products.csv column order so the
importer's field mapping needs no touch-ups. Half portions come through
menu.menu_for() as their own SKUs (<id>-half) at their own price — the
menu.json half_price field is a half-portion price, not a discount, so it is
NOT mapped to sale_price. Kept out of main.py so the feed stays buildable
without the web app importing back into it.
"""
import csv
import io
from pathlib import Path

from . import menu

MENU_LINK = "https://tulsifoods.app/menu"
BRAND = "Tulsi Foods"
GOOGLE_CAT = "Food, Beverages & Tobacco > Food"
HALF_SUFFIX = "-half"
DISH_PHOTO_DIR = Path("app/static/img/dishes")

HEADER = [
    "id", "title", "description", "availability", "condition", "link",
    "image_link", "brand", "price", "google_product_category",
    "fb_product_category", "quantity_to_sell_on_facebook", "sale_price",
    "sale_price_effective_date", "item_group_id", "gender", "color", "size",
    "age_group", "material", "pattern", "shipping", "shipping_weight",
    "offer_disclaimer", "offer_disclaimer_url", "video[0].url",
    "video[0].tag[0]", "gtin", "product_tags[0]", "product_tags[1]", "style[0]",
]

FILL_DESCRIPTIONS = {
    "mini-samosa": "Crisp, golden samosas with a spiced veg filling, served hot with chutney.",
    "aloo-dum": "Baby potatoes in a spicy onion-tomato gravy.",
    "aloo-gobi": "Dry-cooked potato and cauliflower sabzi, tempered with cumin.",
    "aloo-pakoda": "Potatoes coated in gram-flour batter and deep-fried.",
    "aloo-sabzi": "Comforting potato sabzi cooked in a mild onion-tomato gravy.",
    "aloo-sandwich": "Spiced potato filling grilled between bread slices.",
    "bhindi-ki-sabzi": "Okra sauteed with onions and mild spices, home-style.",
    "bread-chat": "Crisp bread pieces tossed with chaat chutneys, yogurt and sev.",
    "chilli-cheeesetoast": "Toasted bread topped with spiced chilli-cheese.",
    "churmur-chat": "Puffed rice mixed with spiced peas, onion, chutney and sev.",
    "curd-rice": "Steamed rice folded into cool tempered curd, with tadka.",
    "dahi-puri-6pcs": "Crisp puris topped with yogurt, chutneys and sev (6 pcs).",
    "extra-bhatura": "An extra fluffy bhatura to go with your chole.",
    "extra-pav": "An extra soft pav bun to go with your bhaji.",
    "kadai-ki-puri": "Crisp, flaky pooris served fresh off the tawa.",
    "raita-extra-curd": "Extra fresh curd to cool things down.",
    "water-bottle-300-ml": "Sealed 300 ml water bottle.",
}


def dish_photo_ids() -> set[str]:
    if not DISH_PHOTO_DIR.is_dir():
        return set()
    return {p.stem for p in DISH_PHOTO_DIR.glob("*.jpg")}


def _description(item: dict) -> str:
    desc = item.get("description") or FILL_DESCRIPTIONS.get(item["id"], "")
    if item["id"].endswith(HALF_SUFFIX):
        return "Half portion. " + desc
    return desc


def _row(item: dict, photos: set[str]) -> list[str]:
    image = ""
    photo_id = item.get("photo_id") or item["id"]
    if photo_id in photos:
        image = f"https://tulsifoods.app/static/img/dishes/{photo_id}.jpg"
    return [
        item["id"], item["name"], _description(item), "in stock", "new",
        MENU_LINK, image, BRAND, f"{item['price']} INR", GOOGLE_CAT, "", "",
        "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
        "", "",
    ]


def catalog_rows() -> list[list[str]]:
    photos = dish_photo_ids()
    items = sorted(menu.menu_for(), key=lambda i: (i["group"], i["name"].lower()))
    return [_row(item, photos) for item in items]


def catalog_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    w.writerows(catalog_rows())
    return buf.getvalue()