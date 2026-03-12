from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics, permissions

from ..querysets import listing_fetch_queryset
from ..serializers import ListingSerializer


@extend_schema(
    tags=["listings"],
    summary="List my listings",
    description="Retrieve all listings owned by the currently authenticated user.",
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
class MyListingsView(generics.ListAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return listing_fetch_queryset().filter(user=self.request.user)
