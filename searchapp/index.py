from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.conf import settings

from listings.models import Listing, ListingAttributeValue, ListingMedia
from taxonomy.models import Category, Location

from .opensearch_client import get_client


def index_name() -> str:
    prefix = getattr(settings, "OPENSEARCH_INDEX_PREFIX", "olxclone")
    version = getattr(settings, "OPENSEARCH_INDEX_VERSION", 1)
    return f"{prefix}_listings_v{version}"


def mapping_body() -> Dict[str, Any]:
    return {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
            "analysis": {
                "analyzer": {
                    "folding": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    }
                }
            },
        },
        "mappings": {
            "dynamic": "false",
            "properties": {
                "id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "folding"},
                "description": {"type": "text", "analyzer": "folding"},
                "category_path": {"type": "keyword"},
                "location_path": {"type": "keyword"},
                "location_name_ru": {"type": "keyword"},
                "location_name_uz": {"type": "keyword"},
                "price": {"type": "double"},
                "price_normalized": {"type": "double"},
                "currency": {"type": "keyword"},
                "condition": {"type": "keyword"},
                "geo": {"type": "geo_point"},
                "refreshed_at": {"type": "date"},
                "quality_score": {"type": "double"},
                "attrs": {
                    "type": "nested",
                    "properties": {
                        "key": {"type": "keyword"},
                        "type": {"type": "keyword"},
                        "value_text": {"type": "keyword"},
                        "value_number": {"type": "double"},
                        "value_bool": {"type": "boolean"},
                        "value_option_key": {"type": "keyword"},
                    },
                },
                "media_urls": {"type": "keyword"},
            },
        },
    }


def ensure_index():
    client = get_client()
    if not client:
        return
    idx = index_name()
    if not client.indices.exists(index=idx):  # type: ignore[attr-defined]
        client.indices.create(index=idx, body=mapping_body())  # type: ignore[attr-defined]


def build_document(listing: Listing) -> Dict[str, Any]:
    # Build category path up to root
    cat_path: List[str] = []
    cat = listing.category
    while cat:
        cat_path.append(cat.slug)
        cat = cat.parent  # type: ignore[attr-defined]
    cat_path.reverse()

    # Location path
    loc_path: List[str] = []
    loc = listing.location
    while loc:
        loc_path.append(loc.slug)
        loc = loc.parent  # type: ignore[attr-defined]
    loc_path.reverse()
    # Location names (ru/uz) for display in search cards
    loc_display_ru = listing.location.name_ru or listing.location.name or ""
    loc_display_uz = listing.location.name_uz or listing.location.name or ""

    # Attributes
    attr_rows = (
        ListingAttributeValue.objects.filter(listing=listing).select_related("attribute")
    )
    attrs: List[Dict[str, Any]] = []
    for row in attr_rows:
        a = row.attribute
        attrs.append(
            {
                "key": a.key,
                "type": a.type,
                "value_text": row.value_text or None,
                "value_number": row.value_number,
                "value_bool": row.value_bool,
                "value_option_key": row.value_option_key or None,
            }
        )

    # Media URLs (first few only)
    media = ListingMedia.objects.filter(listing=listing).order_by("order", "id")[:5]
    media_urls = [m.image.url for m in media if m.image]

    # Normalize price to base currency (UZS) for consistent sorting
    from currency.services import CurrencyService

    price_normalized = float(
        CurrencyService.normalize_price_to_base(listing.price_amount or 0, listing.price_currency)
    )

    doc = {
        "id": str(listing.id),
        "user_id": str(listing.user_id),
        "title": listing.title,
        "description": listing.description,
        "category_path": cat_path,
        "location_path": loc_path,
        "location_name_ru": loc_display_ru,
        "location_name_uz": loc_display_uz,
        "price": float(listing.price_amount or 0),
        "price_normalized": price_normalized,
        "currency": listing.price_currency,
        "condition": listing.condition,
        "geo": {"lat": listing.lat, "lon": listing.lon} if listing.lat and listing.lon else None,
        "refreshed_at": listing.refreshed_at,
        "quality_score": listing.quality_score,
        "attrs": attrs,
        "media_urls": media_urls,
    }
    return doc


def index_listing(listing_id: int):
    client = get_client()
    if not client:
        return
    ensure_index()
    try:
        listing = Listing.objects.select_related("category", "location").get(id=listing_id)
    except Listing.DoesNotExist:
        delete_listing(listing_id)
        return
    doc = build_document(listing)
    client.index(index=index_name(), id=str(listing_id), body=doc)  # type: ignore[arg-type]


def delete_listing(listing_id: int):
    client = get_client()
    if not client:
        return
    try:
        client.delete(index=index_name(), id=str(listing_id))
    except Exception:
        pass
