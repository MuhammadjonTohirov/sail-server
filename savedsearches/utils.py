from __future__ import annotations

from typing import Any, Dict, List

from searchapp.views.opensearch_client import get_client
from searchapp.views.index import index_name


def count_new_items_for_saved_search(saved_search) -> int:
    """
    Count new items matching the saved search query since last_viewed_at.

    Args:
        saved_search: SavedSearch instance

    Returns:
        Number of new items matching the search criteria
    """
    client = get_client()
    if not client:
        return 0

    # If never viewed, return 0 (avoid showing counts for brand new searches)
    if not saved_search.last_viewed_at:
        return 0

    query = saved_search.query or {}

    # Build the OpenSearch query from saved search parameters
    must: List[Dict[str, Any]] = []
    filter_clauses: List[Dict[str, Any]] = []

    # Extract search parameters
    params = query.get("params", query)

    # Text search
    if q := params.get("q"):
        must.append({
            "multi_match": {
                "query": q,
                "fields": ["title^2", "description"],
                "type": "best_fields",
            }
        })

    # Category filter
    if category_slug := params.get("category_slug"):
        filter_clauses.append({"terms": {"category_path": [category_slug]}})

    # Location filter
    if location_slug := params.get("location_slug"):
        filter_clauses.append({"term": {"location_slug": location_slug}})

    # Condition filter
    if condition := params.get("condition"):
        filter_clauses.append({"term": {"condition": condition}})

    # User filter
    if user_id := params.get("user_id"):
        filter_clauses.append({"term": {"user_id": user_id}})

    # Price range filter with currency support
    currency = params.get("currency", "UZS")
    price_min = params.get("price_min") or params.get("min_price")
    price_max = params.get("price_max") or params.get("max_price")

    if price_min is not None or price_max is not None:
        price_range: Dict[str, Any] = {}
        if price_min is not None:
            try:
                price_range["gte"] = float(price_min)
            except (ValueError, TypeError):
                pass
        if price_max is not None:
            try:
                price_range["lte"] = float(price_max)
            except (ValueError, TypeError):
                pass

        if price_range:
            # Filter by price in the specified currency or normalized price in UZS
            if currency == "UZS":
                filter_clauses.append({"range": {"price_normalized_uzs": price_range}})
            else:
                # For other currencies, filter by both currency and price
                filter_clauses.append({"term": {"price_currency": currency}})
                filter_clauses.append({"range": {"price_amount": price_range}})

    # Handle custom attributes
    if "attrs" in params:
        attrs = params["attrs"]
        if isinstance(attrs, dict):
            for attr_key, attr_values in attrs.items():
                if not isinstance(attr_values, list):
                    attr_values = [attr_values]
                filter_clauses.append({
                    "nested": {
                        "path": "attributes",
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"attributes.key": attr_key}},
                                    {"terms": {"attributes.value": attr_values}},
                                ]
                            }
                        }
                    }
                })

    # Add date filter for items created after last_viewed_at
    filter_clauses.append({
        "range": {
            "created_at": {
                "gt": saved_search.last_viewed_at.isoformat()
            }
        }
    })

    # Add status filter (only active listings)
    filter_clauses.append({"term": {"status": "active"}})

    # Build the complete query
    bool_query: Dict[str, Any] = {}
    if must:
        bool_query["must"] = must
    if filter_clauses:
        bool_query["filter"] = filter_clauses

    body = {
        "query": {"bool": bool_query} if bool_query else {"match_all": {}},
        "size": 0,  # We only need the count
        "track_total_hits": True,
    }

    try:
        response = client.search(index=index_name(), body=body)
        total = response.get("hits", {}).get("total", {})

        # Handle both dict format and int format
        if isinstance(total, dict):
            return total.get("value", 0)
        return int(total) if total else 0
    except Exception as e:
        # Log error but don't fail
        print(f"Error counting new items for saved search {saved_search.id}: {e}")
        return 0
