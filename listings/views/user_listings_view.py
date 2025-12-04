from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..serializers import ListingSerializer


class UserListingsView(generics.ListAPIView):
    """Get all active listings for a specific user (public view)"""
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        queryset = Listing.objects.filter(
            user_id=user_id,
            status=Listing.Status.ACTIVE
        ).select_related("category", "location", "user").prefetch_related("media")

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
