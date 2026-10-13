"""Branded square image for every dish without a photo, for the WhatsApp /
Meta catalogue (which rejects items without an image). Run after adding
dishes:  python scripts/make_catalog_cards.py   (needs Pillow; dev-only).
Real photos in app/static/img/dishes/ always win over these cards."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import menu  # noqa: E402

OUT = ROOT / "app/static/img/cards"
PHOTOS = ROOT / "app/static/img/dishes"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BG, INK, GREEN, SUB = "#FBF8F2", "#171A14", "#0E7A45", "#6F7468"
S = 1080


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def card(item: dict) -> Image.Image:
    im = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(im)
    d.text((90, 96), "TULSI FOODS · MYLAPORE", font=ImageFont.truetype(BOLD, 34), fill=GREEN)
    # Indian veg mark: green square outline with a green dot.
    d.rectangle((S - 160, 84, S - 90, 154), outline=GREEN, width=7)
    d.ellipse((S - 143, 101, S - 107, 137), fill=GREEN)
    name = item["name"]
    for size in (112, 96, 84, 72, 62):
        font = ImageFont.truetype(BOLD, size)
        lines = wrap(d, name, font, S - 180)
        if len(lines) <= 4:
            break
    lh = int(size * 1.15)
    y = (S - lh * len(lines)) // 2 - 40
    for ln in lines:
        d.text((90, y), ln, font=font, fill=INK)
        y += lh
    d.text((90, y + 30), item.get("group", ""), font=ImageFont.truetype(REG, 44), fill=SUB)
    d.rectangle((0, S - 170, S, S), fill=GREEN)
    d.text((90, S - 112), "Pure vegetarian · home-style North Indian",
           font=ImageFont.truetype(BOLD, 38), fill="white")
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    photos = {p.stem for p in PHOTOS.glob("*.jpg")}
    made = 0
    for item in menu.load_menu():
        if item["id"] in photos:
            continue
        card(item).resize((800, 800), Image.LANCZOS).save(
            OUT / f"{item['id']}.jpg", quality=80, optimize=True)
        made += 1
    print(f"{made} cards in {OUT}")


if __name__ == "__main__":
    main()
