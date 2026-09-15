"""Data-driven FAQ answers.

Every answer is generated from live config / menu data (delivery zones, fees,
minimums, opening hours, real menu prices) so the visible FAQ and the
FAQPage JSON-LD can never drift from what the site actually does.
"""
from .config import MONDAY_OPENS_AT, OPENING_HOURS, STORE_WHATSAPP


def _hhmm_to_12h(hhmm: str) -> str:
    h, m = hhmm.split(":")
    h = int(h)
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m} {suffix}".replace(":00 ", " ")


def _open_text() -> str:
    wk_open, wk_close = OPENING_HOURS["mon_sat"]
    su_open, su_close = OPENING_HOURS["sunday"]
    return (
        f"Monday to Saturday {_hhmm_to_12h(wk_open)} to {_hhmm_to_12h(wk_close)}, "
        f"Sunday {_hhmm_to_12h(su_open)} to {_hhmm_to_12h(su_close)}"
    )


def _fee_text(zones) -> str:
    parts = [f"₹{z['fee']} up to {z['max_km']:.0f} km" for z in zones]
    return ", ".join(parts)


def _min_order_text(zones) -> str:
    return ", ".join(
        f"₹{z['min_order']} within {z['max_km']:.0f} km" for z in zones
    )


def delivery_faqs(zones, free_above) -> list[dict]:
    """Delivery-page FAQs, keyed to the focus queries people actually search."""
    zones = sorted(zones, key=lambda z: z["max_km"])
    return [
        {
            "q": "How much does Tulsi Foods delivery cost?",
            "a": (
                f"Tulsi Foods estimates delivery at {_fee_text(zones)} from the "
                f"kitchen in Alwarpet, Chennai. Delivery is free on orders over "
                f"₹{free_above}, and the kitchen confirms the exact fee before you pay."
            ),
        },
        {
            "q": "How long does Tulsi Foods delivery take?",
            "a": (
                "Thirty to sixty minutes, depending on the dish and how busy the "
                "kitchen is. Thalis and parathas are cooked after you order, not held. "
                "Orders placed ahead for a set time leave the kitchen for that hour."
            ),
        },
        {
            "q": "Does Tulsi Foods deliver to my area?",
            "a": (
                f"Tulsi Foods delivers anywhere within {zones[-1]['max_km']:.0f} km of "
                "the Murrays Gate Road kitchen in Alwarpet — covering Mylapore, "
                "Alwarpet, Royapettah, Teynampet, Nandanam, R.A. Puram, Adyar, "
                "T. Nagar and Egmore. Farther than that is pickup in Alwarpet or "
                "catering by arrangement."
            ),
        },
        {
            "q": "How do I order ahead at Tulsi Foods?",
            "a": (
                "Tell us a time and the food leaves the kitchen for it, up to two "
                "weeks in advance. Lunch and dinner get busy, so an hour's notice "
                "means it reaches you hot."
            ),
        },
        {
            "q": "How can I pay at Tulsi Foods?",
            "a": (
                "UPI when you order, or cash to the rider. The total at checkout "
                "already includes the estimated delivery charge, so nothing is "
                "added at the door."
            ),
        },
        {
            "q": "Is there a minimum order for delivery at Tulsi Foods?",
            "a": (
                f"Yes — {_min_order_text(zones)}. The checkout shows what your "
                "area needs before you submit."
            ),
        },
    ]


def landing_faqs(zones, free_above, price_range, has_upi) -> list[dict]:
    """Homepage FAQs, keyed to the focus keywords from the hero and meta."""
    zones = sorted(zones, key=lambda z: z["max_km"])
    repay = "UPI at checkout, or cash on delivery" if has_upi else "cash or by message"
    return [
        {
            "q": "Is Tulsi Foods a pure vegetarian restaurant in Mylapore, Chennai?",
            "a": (
                "Yes — Tulsi Foods is a 100% pure vegetarian, home-style North Indian "
                "kitchen in Mylapore, Chennai, run by Kavita Lath since 2015. Jain and "
                "no-onion-garlic versions are cooked separately on request."
            ),
        },
        {
            "q": "What are Tulsi Foods' opening hours?",
            "a": (
                f"{_open_text()}. Monday is a half-day for online orders until "
                f"{_hhmm_to_12h(MONDAY_OPENS_AT)}."
            ),
        },
        {
            "q": "Does Tulsi Foods deliver in Chennai, and what does it cost?",
            "a": (
                "Yes — anywhere within 7 km of the kitchen in Alwarpet: Mylapore, "
                "Alwarpet, Royapettah, Teynampet, R.A. Puram, Adyar, T. Nagar and "
                f"Egmore. Estimated delivery is {_fee_text(zones)} "
                f"(free over ₹{free_above}); the kitchen confirms the exact fee."
            ),
        },
        {
            "q": "How much does food at Tulsi Foods cost?",
            "a": (
                f"Menu prices run from about ₹{price_range[0]} to ₹{price_range[1]} "
                "— thalis and lunch plates sit in the middle, snacks, drinks and "
                "small plates cost less. Halves of many sabzi and dal dishes are "
                "available."
            ),
        },
        {
            "q": "How do I order from Tulsi Foods?",
            "a": (
                "Pick your dishes from the menu on this site and check out, or message "
                f"the kitchen on WhatsApp at {STORE_WHATSAPP}. Pay {repay}."
            ),
        },
        {
            "q": "Does Tulsi Foods cook food fresh to order?",
            "a": (
                "Yes. Thalis and parathas are cooked after you order, which is why "
                "delivery takes 30 to 60 minutes — nothing is pre-made and reheated."
            ),
        },
    ]