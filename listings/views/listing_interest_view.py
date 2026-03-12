from __future__ import annotations

from django.db.models import F
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingInterestView(APIView):
    """
    POST /api/v1/listings/<pk>/interest
    Track that a user showed interest in a listing (e.g., revealed phone number).
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["listings"],
        summary="Track listing interest",
        description="Record that a user showed interest in a listing, "
        "for example by revealing the seller's phone number. Increments the interest counter.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"tracked": True},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(id=pk, status=Listing.Status.ACTIVE)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        tracked = not request.user.is_authenticated or request.user.id != listing.user_id
        if tracked:
            Listing.objects.filter(id=pk).update(interest_count=F("interest_count") + 1)

        return Response({"tracked": tracked}, status=status.HTTP_200_OK)
