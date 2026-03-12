from __future__ import annotations

import random
from decimal import Decimal


DEFAULT_BLUEPRINT = {
    "titles": ["Ready to use item", "Well-kept product", "Neat listing"],
    "modifiers": ["with full details", "in good condition", "from owner"],
    "features": ["clean photos", "quick handover", "reasonable price"],
    "price_min": 100_000,
    "price_max": 1_000_000,
    "condition_new_ratio": 0.25,
    "seller_business_ratio": 0.15,
}

CATEGORY_BLUEPRINTS: dict[str, dict] = {
    "smartphones": {
        "titles": ["iPhone 14 128GB", "Samsung Galaxy A54", "Xiaomi Redmi Note 13", "Google Pixel 7"],
        "modifiers": ["with charger", "dual SIM", "factory reset", "clean IMEI"],
        "features": ["battery works well", "screen without cracks", "used carefully"],
        "price_min": 1_800_000,
        "price_max": 12_500_000,
    },
    "laptops": {
        "titles": ["MacBook Air M1", "Dell Inspiron 15", "Lenovo IdeaPad 5", "ASUS VivoBook"],
        "modifiers": ["for study", "for office work", "SSD included", "with original charger"],
        "features": ["keyboard and screen are clean", "ready for daily use", "fast boot time"],
        "price_min": 3_500_000,
        "price_max": 16_000_000,
    },
    "tablets": {
        "titles": ["iPad 9th Gen", "Samsung Galaxy Tab A9", "Lenovo Tab M10", "Xiaomi Pad 6"],
        "modifiers": ["Wi-Fi version", "with case", "for children", "lightly used"],
        "features": ["touch works perfectly", "battery lasts well", "good for media and study"],
        "price_min": 1_200_000,
        "price_max": 7_000_000,
    },
    "tv-audio": {
        "titles": ["LG Smart TV 43", "Samsung Soundbar", "Sony Bravia 50", "JBL PartyBox"],
        "modifiers": ["remote included", "clear sound", "wall mount ready", "good screen quality"],
        "features": ["tested before sale", "works without issues", "kept in apartment use"],
        "price_min": 900_000,
        "price_max": 9_000_000,
    },
    "cars": {
        "titles": ["Chevrolet Cobalt", "Kia K5", "Hyundai Elantra", "BYD Song Plus"],
        "modifiers": ["clean paperwork", "second owner", "serviced on time", "gas installed"],
        "features": ["body in decent shape", "interior is tidy", "drives smoothly"],
        "price_min": 75_000_000,
        "price_max": 350_000_000,
        "condition_new_ratio": 0.08,
        "seller_business_ratio": 0.25,
    },
    "motorcycles": {
        "titles": ["Yamaha NMAX", "Lifan KP Mini", "Honda CB300", "Bajaj Pulsar"],
        "modifiers": ["documents ready", "city use", "starter works well", "fresh service"],
        "features": ["good tires", "engine starts easily", "comfortable for daily rides"],
        "price_min": 9_000_000,
        "price_max": 55_000_000,
        "condition_new_ratio": 0.15,
        "seller_business_ratio": 0.2,
    },
    "auto-parts": {
        "titles": ["Original headlight set", "Engine spare parts", "Front bumper", "Radiator assembly"],
        "modifiers": ["for Chevrolet", "good used condition", "from dismantled car", "ready to install"],
        "features": ["no hidden defects", "can send extra photos", "price for one set"],
        "price_min": 150_000,
        "price_max": 8_000_000,
    },
    "tires-wheels": {
        "titles": ["Summer tire set", "Winter tire pair", "Alloy wheels R16", "Original wheel set"],
        "modifiers": ["balanced", "good tread", "without repairs", "from personal car"],
        "features": ["stored properly", "fit check available", "sold as shown in photos"],
        "price_min": 300_000,
        "price_max": 9_000_000,
    },
    "apartments": {
        "titles": ["2-room apartment", "Studio apartment", "3-room apartment", "Renovated flat"],
        "modifiers": ["near metro", "owner listing", "good floor plan", "with furniture"],
        "features": ["documents are ready", "quiet neighborhood", "suitable for living or rent"],
        "price_min": 220_000_000,
        "price_max": 1_800_000_000,
        "condition_new_ratio": 0.2,
        "seller_business_ratio": 0.35,
    },
    "houses": {
        "titles": ["Family house", "Yard house", "Newly built house", "House with plot"],
        "modifiers": ["with garden", "near main road", "full documents", "spacious rooms"],
        "features": ["water and electricity connected", "good for large family", "can arrange viewing"],
        "price_min": 350_000_000,
        "price_max": 3_000_000_000,
        "condition_new_ratio": 0.18,
        "seller_business_ratio": 0.28,
    },
    "commercial": {
        "titles": ["Retail space", "Office for rent/sale", "Warehouse unit", "Commercial building"],
        "modifiers": ["busy location", "separate entrance", "ready business area", "good frontage"],
        "features": ["high foot traffic", "suitable for office or shop", "documents in order"],
        "price_min": 450_000_000,
        "price_max": 4_000_000_000,
        "condition_new_ratio": 0.15,
        "seller_business_ratio": 0.6,
    },
    "land": {
        "titles": ["Residential land plot", "Corner plot", "Land near highway", "Empty plot with documents"],
        "modifiers": ["for construction", "good location", "straight roads", "owner sale"],
        "features": ["cadastre available", "boundaries are clear", "can discuss price after viewing"],
        "price_min": 120_000_000,
        "price_max": 1_500_000_000,
        "condition_new_ratio": 0.02,
        "seller_business_ratio": 0.12,
    },
    "womens-clothing": {
        "titles": ["Dress collection", "Women's jacket", "Evening dress", "Seasonal clothing set"],
        "modifiers": ["new with tag", "lightly worn", "popular size", "trendy style"],
        "features": ["clean and ready to wear", "fabric feels good", "kept carefully"],
        "price_min": 120_000,
        "price_max": 1_500_000,
        "condition_new_ratio": 0.45,
    },
    "mens-clothing": {
        "titles": ["Men's jacket", "Classic suit", "Casual clothing set", "Winter coat"],
        "modifiers": ["good size range", "new collection", "for office", "worn a few times"],
        "features": ["clean condition", "comfortable fit", "good for everyday use"],
        "price_min": 140_000,
        "price_max": 1_800_000,
        "condition_new_ratio": 0.4,
    },
    "shoes": {
        "titles": ["Leather shoes", "Running sneakers", "Kids shoes", "Seasonal boots"],
        "modifiers": ["original pair", "almost new", "comfortable sole", "popular model"],
        "features": ["clean inside and out", "no major wear", "ready for immediate use"],
        "price_min": 160_000,
        "price_max": 2_200_000,
        "condition_new_ratio": 0.38,
    },
    "accessories": {
        "titles": ["Watch", "Handbag", "Backpack", "Sunglasses"],
        "modifiers": ["gift condition", "stylish design", "original item", "limited use"],
        "features": ["kept carefully", "good for everyday use", "matches the photos"],
        "price_min": 90_000,
        "price_max": 3_500_000,
        "condition_new_ratio": 0.42,
    },
    "toys": {
        "titles": ["Educational toy set", "Building blocks", "Soft toy", "Remote control car"],
        "modifiers": ["for preschool age", "clean condition", "gift ready", "with all parts"],
        "features": ["safe for kids", "used carefully", "bright colors and neat condition"],
        "price_min": 70_000,
        "price_max": 1_200_000,
        "condition_new_ratio": 0.5,
    },
    "baby-strollers": {
        "titles": ["Baby stroller", "Travel stroller", "2-in-1 stroller", "Compact stroller"],
        "modifiers": ["folds easily", "good wheels", "light frame", "clean fabric"],
        "features": ["used carefully", "comfortable for walks", "all mechanisms work"],
        "price_min": 600_000,
        "price_max": 4_800_000,
        "condition_new_ratio": 0.22,
    },
    "kids-clothing": {
        "titles": ["Kids clothing set", "School uniform", "Winter jacket for kids", "Baby clothing bundle"],
        "modifiers": ["clean and sorted", "season ready", "good quality fabric", "popular sizes"],
        "features": ["washed and ready to use", "no hidden defects", "comfortable materials"],
        "price_min": 80_000,
        "price_max": 900_000,
        "condition_new_ratio": 0.46,
    },
    "school-supplies": {
        "titles": ["School backpack", "Stationery bundle", "Study desk set", "Notebook and pen pack"],
        "modifiers": ["for new term", "unused", "neat condition", "good quality"],
        "features": ["ready for school", "clean and practical", "suitable for daily study"],
        "price_min": 50_000,
        "price_max": 1_500_000,
        "condition_new_ratio": 0.52,
    },
}


def build_listing_payload(category_slug: str, rng: random.Random, sequence: int) -> dict:
    blueprint = {**DEFAULT_BLUEPRINT, **CATEGORY_BLUEPRINTS.get(category_slug, {})}

    title = f"{rng.choice(blueprint['titles'])} {rng.choice(blueprint['modifiers'])}".strip()
    description = (
        f"{title}. "
        f"{rng.choice(blueprint['features']).capitalize()}. "
        f"Listing #{sequence:03d} prepared for development and UI testing."
    )

    price = rng.randint(blueprint["price_min"], blueprint["price_max"])
    price = max(price - (price % 10_000), 10_000)

    return {
        "title": title,
        "description": description,
        "price_amount": Decimal(str(price)),
        "condition": "new" if rng.random() < blueprint.get("condition_new_ratio", 0.25) else "used",
        "seller_type": "business" if rng.random() < blueprint.get("seller_business_ratio", 0.15) else "person",
        "is_price_negotiable": rng.random() < 0.4,
    }
