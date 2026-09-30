"""Search aliases: the other names people type for the dishes we actually cook.

Rules (see docs/SEO_PLAYBOOK.md §6):
- Only TRUE synonyms, regional names and common spellings of the SAME dish
  ("Chole Bhature" for Chola Bhatura, "Golgappa" for Pani Puri, "Rose Milk"
  for Rose Milkshake). Never a different dish we don't serve (e.g. no
  "Paneer Lababdar" on Paneer Butter Masala) — Google treats that as a
  mismatch, users bounce, and the page ranks worse, not better.
- Broad intents ("paneer curry", "veg meals", "street food") live at category
  level in CATEGORY_KEYWORDS, where a broad search should land.
- "near me" is decided by Google from the searcher's location + our Google
  Business Profile; on-page, the honest lever is naming the real
  neighbourhoods we deliver to (NEARBY_AREAS) next to the dish.
"""

# Neighbourhoods the kitchen actually serves (mirrors the /delivery table).
NEARBY_AREAS = [
    "Mylapore", "Alwarpet", "Teynampet", "Royapettah", "Mandaveli",
    "Abhiramapuram", "R.A. Puram", "Nandanam", "Gopalapuram",
    "Adyar", "T. Nagar", "Egmore",
]

DISH_ALIASES: dict[str, list[str]] = {
    # Thalis & Combos
    "north-indian-thali": ["North Indian Meals", "Veg Thali", "North Indian Veg Meals"],
    "mini-thali": ["Mini Meals", "Small Veg Thali"],
    "rajasthani-thali": ["Marwari Thali", "Dal Baati Thali", "Rajasthani Meals"],
    "executive-combo": ["Roti Sabzi Combo", "Phulka Combo", "Veg Lunch Combo"],
    "classic-dal-rice": ["Dal Chawal", "Dal Rice"],
    "dal-makhani-rice-bowl": ["Dal Makhani Chawal", "Dal Makhani Rice"],
    "paneer-butter-masala-rice-bowl": ["Paneer Makhani Rice Bowl", "Paneer Rice Bowl"],
    # Parathas & Breads
    "phulka": ["Chapati", "Chapathi", "Roti", "Fulka"],
    "plain-roti": ["Chapati", "Chapathi", "Tawa Roti"],
    "tandoori-roti": ["Tandoor Roti", "Tandoori Chapati"],
    "aloo-paratha": ["Aloo Parantha", "Alu Paratha", "Potato Paratha", "Aloo Parotta"],
    "gobi-paratha": ["Gobhi Paratha", "Gobi Parantha", "Cauliflower Paratha"],
    "paneer-paratha": ["Paneer Parantha", "Paneer Stuffed Paratha"],
    "peas-paratha": ["Matar Paratha", "Mutter Paratha", "Green Peas Paratha"],
    "plain-paratha": ["Paratha", "Parantha", "Tawa Paratha"],
    "chola-bhatura": ["Chole Bhature", "Chole Bhatura", "Chhole Bhature", "Chana Bhatura", "Chole Batura"],
    "extra-bhatura": ["Bhatura", "Bhature"],
    "masala-kulcha": ["Aloo Kulcha", "Stuffed Kulcha"],
    "plain-kulcha": ["Kulcha"],
    "butter-naan": ["Butter Nan"],
    "garlic-naan": ["Garlic Nan", "Lehsuni Naan"],
    "naan": ["Plain Naan", "Nan"],
    "baby-cheese-naan-2pcs": ["Cheese Naan", "Mini Cheese Naan"],
    "kadai-ki-puri": ["Puri", "Poori", "Kadai Puri"],
    # Sabzi
    "paneer-butter-masala": ["Paneer Makhani", "Butter Paneer", "Paneer Makhanwala"],
    "mutter-paneer": ["Matar Paneer", "Mattar Paneer", "Peas Paneer"],
    "palak-paneer": ["Saag Paneer", "Spinach Paneer"],
    "malai-kofta": ["Malai Kofta Curry"],
    "vegetable-kofta": ["Veg Kofta", "Veg Kofta Curry"],
    "dal-makhani": ["Dal Makhni", "Maa Ki Dal", "Kaali Dal", "Black Dal"],
    "dal-tadka": ["Dal Fry", "Tadka Dal", "Yellow Dal Tadka", "Dal Tarka"],
    "channa-masala": ["Chana Masala", "Chole Masala", "Chole", "Chickpea Curry"],
    "mixed-vegetable": ["Mix Veg", "Mixed Veg Curry", "Mix Veg Sabzi"],
    "aloo-gobi": ["Aloo Gobhi", "Alu Gobi", "Potato Cauliflower Curry"],
    "aloo-sabzi": ["Aloo Ki Sabzi", "Aloo Curry", "Potato Curry", "Aloo Bhaji"],
    "aloo-dum": ["Dum Aloo", "Dum Aloo Curry"],
    "bhindi-ki-sabzi": ["Bhindi Masala", "Bhindi Fry", "Ladies Finger Fry", "Okra Curry"],
    "gobi-masala": ["Gobhi Masala", "Cauliflower Masala"],
    "peas-masala": ["Matar Masala", "Green Peas Masala", "Mutter Masala"],
    "pakodi-ki-kadi": ["Kadhi Pakora", "Kadhi Pakoda", "Pakora Kadhi", "Punjabi Kadhi"],
    "kadi": ["Kadhi", "Dahi Kadhi", "Besan Kadhi"],
    # Chaats & Snacks
    "pani-puri": ["Golgappa", "Gol Gappe", "Puchka", "Phuchka", "Panipuri", "Pani Poori"],
    "papdi-chat-6pcs": ["Papdi Chaat", "Papri Chaat", "Papri Chat"],
    "dahi-papdi-chat-6pcs": ["Dahi Papdi Chaat", "Dahi Papri Chaat"],
    "dahi-puri-6pcs": ["Dahi Poori", "Dahi Batata Puri"],
    "bhel-puri": ["Bhel", "Bhelpuri", "Mumbai Bhel"],
    "samosa-2pcs": ["Aloo Samosa", "Singara"],
    "mini-samosa": ["Cocktail Samosa", "Small Samosa"],
    "samosa-chat": ["Samosa Chaat"],
    "aloo-tikki-2pcs": ["Alu Tikki", "Potato Tikki", "Aloo Patties"],
    "dahi-aloo-tikki-2pcs": ["Dahi Tikki", "Dahi Aloo Tikki Chaat"],
    "corn-aloo-tikki-2pcs": ["Corn Tikki", "Corn Potato Tikki"],
    "chola-tikki-2pcs": ["Chole Tikki", "Chole Tikki Chaat", "Chana Tikki"],
    "pav-bhaji": ["Pao Bhaji", "Bhaji Pav", "Mumbai Pav Bhaji"],
    "vada-pav": ["Vada Pao", "Wada Pav", "Batata Vada Pav", "Mumbai Vada Pav"],
    "extra-pav": ["Pav", "Extra Pao"],
    "sabudana-vada-2pcs": ["Sabudana Wada", "Sago Vada", "Javvarisi Vadai"],
    "dhokla": ["Gujarati Dhokla"],
    "dhokla-chat": ["Dhokla Chaat"],
    "poha": ["Pohe", "Aval Upma", "Beaten Rice Poha"],
    "cutlet-2pcs": ["Veg Cutlet", "Vegetable Cutlet"],
    "aloo-pakoda": ["Aloo Pakora", "Potato Pakoda", "Potato Bajji"],
    "onion-pakoda": ["Onion Pakora", "Onion Bhaji", "Pyaaz Pakoda", "Kanda Bhaji"],
    "masala-papad": ["Papad Masala"],
    "roasted-papad": ["Papad", "Plain Papad"],
    "bread-chat": ["Bread Chaat"],
    "churmur-chat": ["Churmur", "Churmur Chaat"],
    "fruit-chaat": ["Fruit Chat"],
    "chilli-cheeesetoast": ["Chilli Cheese Toast", "Cheese Chilli Toast"],
    "garlic-bread-cheese": ["Cheese Garlic Bread", "Cheesy Garlic Bread"],
    "vegetable-sandwich": ["Veg Sandwich"],
    "grilled-sandwich": ["Veg Grilled Sandwich", "Grill Sandwich"],
    "paneer-sandwich": ["Grilled Paneer Sandwich"],
    "corn-cheese-sandwich": ["Cheese Corn Sandwich", "Sweet Corn Sandwich"],
    "aloo-sandwich": ["Potato Sandwich", "Aloo Masala Sandwich"],
    "raita-extra-curd": ["Extra Curd", "Dahi"],
    # Starters
    "crispy-chilly-paneer": ["Chilli Paneer", "Chilly Paneer", "Paneer Chilli"],
    "crispy-chilly-corn": ["Crispy Corn", "Chilli Corn", "Crispy Chilli Corn"],
    "crispy-chilly-potato": ["Chilli Potato", "Chilly Potato", "Crispy Potato"],
    "gobi-manchurian": ["Gobhi Manchurian", "Cauliflower Manchurian"],
    "paneer-tikka": ["Grilled Paneer Tikka"],
    "kathi-roll": ["Kati Roll", "Veg Roll", "Veg Frankie", "Veg Wrap"],
    "french-fries": ["Fries", "Finger Chips"],
    "garlic-bread": ["Garlic Toast"],
    "nachos": ["Cheese Nachos"],
    "veg-burger": ["Vegetable Burger"],
    "corn-cheese-bun-2pcs": ["Cheese Corn Bun"],
    # Soups & Rice
    "veg-briyani": ["Veg Biryani", "Vegetable Biryani", "Veg Biriyani"],
    "vegetable-pulao": ["Veg Pulao", "Veg Pulav", "Vegetable Pulav"],
    "peas-pulao": ["Matar Pulao", "Mutter Pulao", "Green Peas Pulao"],
    "kaju-vegetable-pulao": ["Kaju Pulao", "Cashew Pulao"],
    "jeera-rice": ["Cumin Rice", "Zeera Rice"],
    "veg-fried-rice": ["Vegetable Fried Rice", "Fried Rice"],
    "curd-rice": ["Thayir Sadam", "Dahi Chawal", "Dahi Rice"],
    "plain-rice": ["Steamed Rice", "White Rice"],
    "vegetable-soup": ["Veg Soup", "Mixed Vegetable Soup"],
    "sweet-corn-soup": ["Veg Sweet Corn Soup", "Corn Soup"],
    "tomato-soup": ["Tamatar Soup"],
    # Italian (+ the noodles that live there)
    "vegetable-hakka-noodles": ["Veg Hakka Noodles", "Hakka Noodles", "Veg Noodles", "Veg Chowmein"],
    "white-sauce-pasta": ["Alfredo Pasta", "Pasta in White Sauce"],
    "mixed-sauce-pasta": ["Pink Sauce Pasta", "Pink Pasta"],
    "penne-arrabiata": ["Penne Arrabbiata", "Red Sauce Pasta", "Arrabbiata Pasta"],
    "cheese-pasta": ["Cheesy Pasta", "Cheese Sauce Pasta"],
    "regular-pizza": ["Veg Pizza"],
    # Chai & Beverages
    "masala-chai": ["Masala Tea", "Spiced Tea"],
    "tea": ["Chai", "Milk Tea"],
    "lemon-tea": ["Nimbu Chai"],
    "buttermilk": ["Chaas", "Chaach", "Neer Mor", "Spiced Buttermilk"],
    "lassi": ["Sweet Lassi", "Punjabi Lassi"],
    "lemonade": ["Nimbu Pani", "Lemon Juice", "Fresh Lime"],
    "mosambi-juice": ["Sweet Lime Juice", "Musambi Juice", "Sathukudi Juice"],
    "watermelon-juice": ["Tarbooz Juice"],
    "orange-juice": ["Fresh Orange Juice"],
    "rose-milkshake": ["Rose Milk"],
    "badam-milkshake": ["Badam Milk", "Almond Milkshake", "Badam Shake"],
    "chocolate-milkshake": ["Chocolate Shake"],
    "vanilla-milkshake": ["Vanilla Shake"],
    "banana-milkshake": ["Banana Shake"],
    "oreo-milkshake": ["Oreo Shake"],
    "cold-coffee": ["Iced Coffee"],
    "cafe-latte": ["Latte"],
    "mint-mojito": ["Virgin Mojito", "Mojito Mocktail"],
    "masala-thumsup": ["Masala Thums Up", "Masala Coke", "Masala Soda"],
    # Desserts
    "gulab-jamun-2pcs": ["Gulab Jamun", "Gulab Jamoon"],
    "rabdi": ["Rabri"],
    "moong-dal-halwa": ["Moong Dal Ka Halwa", "Mung Dal Halwa"],
    "kulfi": ["Kulfi Ice Cream"],
    # Specialities
    "club-kachori-6pcs": ["Kachori", "Kolkata Club Kachori", "Kachori Sabzi"],
    "raita-250ml": ["Raita", "Dahi Raita", "Curd Raita"],
}

# Broad intents per category — what someone types when they don't have a
# specific dish in mind. Shown on the category page + in its title/meta.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Thalis & Combos": ["veg thali", "North Indian meals", "veg lunch", "dal rice"],
    "Parathas & Breads": ["paratha", "roti", "chapati", "naan", "kulcha"],
    "Chaats & Snacks": ["chaat", "pani puri", "pav bhaji", "street food", "evening snacks"],
    "Sabzi": ["paneer curry", "veg curry", "dal", "sabji", "North Indian gravy"],
    "Starters": ["chilli paneer", "Indo-Chinese starters", "veg starters"],
    "Soups & Rice": ["veg biryani", "pulao", "fried rice", "soup", "curd rice"],
    "Chai & Beverages": ["masala chai", "fresh juice", "milkshakes", "mocktails", "rose milk"],
    "Desserts": ["gulab jamun", "rabdi", "kulfi", "Indian sweets", "ice cream"],
    "Italian": ["pasta", "pizza", "hakka noodles"],
    "Specialities": ["club kachori", "raita"],
}


def aliases_for(item_id: str) -> list[str]:
    """Aliases for a menu id (half-portion ids share the full dish's)."""
    return list(DISH_ALIASES.get(item_id.split("__")[0], []))


def item_faqs(name: str, aliases: list[str], price, group: str) -> list[dict]:
    """Three dish-specific Q&As, visible on the page AND as FAQPage JSON-LD.
    Answers are facts true for every dish (location, veg, ordering), so they
    never overclaim for a particular item."""
    aka = f" (also called {', '.join(aliases[:3])})" if aliases else ""
    areas = ", ".join(NEARBY_AREAS[:-1]) + " and " + NEARBY_AREAS[-1]
    return [
        {
            "q": f"Where can I order {name} near Mylapore, Chennai?",
            "a": (f"Tulsi Foods cooks {name}{aka} fresh to order at 34 Murrays Gate Road, "
                  f"Alwarpet, Chennai 600018 — a few minutes from Mylapore. Order online on "
                  f"tulsifoods.app for delivery to {areas}, or pick it up from the kitchen."),
        },
        {
            "q": f"How much is {name} at Tulsi Foods?",
            "a": (f"{name} is ₹{price} on the Tulsi Foods menu ({group}). Ordering direct on "
                  f"tulsifoods.app means no aggregator markup or platform fee."),
        },
        {
            "q": f"Is Tulsi Foods' {name} pure vegetarian?",
            "a": ("Yes. Tulsi Foods is a 100% pure vegetarian kitchen — no egg, no meat, ever. "
                  "Jain and no-onion-garlic versions can be requested in the order note."),
        },
    ]
