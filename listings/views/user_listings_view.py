from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics, permissions

from ..models import Listing
from ..querysets import listing_fetch_queryset
from ..serializers import ListingSerializer


@extend_schema(
    tags=["listings"],
    summary="List user's listings",
    description="Retrieve all active listings for a specific user. "
    "Supports filtering by category slug and sorting by newest, oldest, or price.",
    responses={200: ListingSerializer(many=True)},
    examples=[
        OpenApiExample(
            "Success",
            value={
                "success": True,
                "data": [{"id": 1, "title": "iPhone 15", "status": "active"}],
                "error": None,
                "code": 200,
            },
            response_only=True,
        ),
    ],
)
class UserListingsView(generics.ListAPIView):
    """Get all active listings for a specific user (public view)"""
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        queryset = listing_fetch_queryset().filter(
            user_id=user_id,
            status=Listing.Status.ACTIVE
        )

        # Apply filters
        category_slug = self.request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        sort = self.request.query_params.get("sort", "newest")
        if sort == "newest":
            queryset = queryset.order_by("-refreshed_at", "-created_at")
        elif sort == "oldest":
            queryset = queryset.order_by("refreshed_at", "created_at")
        elif sort == "price_asc":
            queryset = queryset.order_by("price_amount")
        elif sort == "price_desc":
            queryset = queryset.order_by("-price_amount")

        return queryset
