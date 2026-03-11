from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics, permissions

from ..models import Listing
from ..permissions import IsOwnerOrReadOnly
from ..serializers import ListingUpdateSerializer


@extend_schema(
    tags=["listings"],
    summary="Update a listing",
    description="Update an existing listing. Only the listing owner can perform this action.",
    responses={200: ListingUpdateSerializer},
    examples=[
        OpenApiExample(
            "Success",
            value={
                "success": True,
                "data": {"id": 1, "title": "Updated Title", "status": "active"},
                "error": None,
                "code": 200,
            },
            response_only=True,
        ),
    ],
)
class ListingUpdateView(generics.UpdateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
