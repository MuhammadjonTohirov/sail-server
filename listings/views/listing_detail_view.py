from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from django.db.models import Q
from rest_framework import generics, permissions

from ..models import Listing
from ..querysets import listing_fetch_queryset
from ..serializers import ListingSerializer


@extend_schema(
    tags=["listings"],
    summary="Get listing detail",
    description="Retrieve full details of a single listing by its ID.",
    responses={200: ListingSerializer},
    examples=[
        OpenApiExample(
            "Success",
            value={
                "success": True,
                "data": {
                    "id": 1,
                    "title": "iPhone 15",
                    "price_amount": "1000.00",
                    "price_currency": "USD",
                    "status": "active",
                },
                "error": None,
                "code": 200,
            },
            response_only=True,
        ),
    ],
)
class ListingDetailView(generics.RetrieveAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = listing_fetch_queryset()
        request = self.request
        if request.user.is_authenticated:
            return queryset.filter(Q(status=Listing.Status.ACTIVE) | Q(user=request.user))
        return queryset.filter(status=Listing.Status.ACTIVE)
