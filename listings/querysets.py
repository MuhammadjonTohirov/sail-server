from __future__ import annotations

from django.db.models import Count, Prefetch

from .models import Listing, ListingAttributeValue


def listing_fetch_queryset():
    attribute_qs = ListingAttributeValue.objects.select_related("attribute").order_by("attribute_id", "id")
    return (
        Listing.objects.select_related("category", "location", "user", "user__profile")
        .prefetch_related(
            "media",
            Prefetch("attributes", queryset=attribute_qs, to_attr="prefetched_attribute_values"),
        )
        .annotate(favorite_count=Count("favorited_by", distinct=True))
        .order_by("-refreshed_at", "-created_at")
    )
