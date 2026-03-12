from __future__ import annotations

from django.db.models import F
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing
from ..utils import get_listing_contact_details


class ListingRevealContactView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["listings"],
        summary="Reveal listing contact",
        description=(
            "Return the seller contact details for an active listing and "
            "track interest when the viewer is not the listing owner."
        ),
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "contact_name": "Seller Contact",
                        "contact_phone": "+998901112233",
                        "contact_email": "seller@example.com",
                        "tracked": True,
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            listing = Listing.objects.select_related("user", "user__profile").get(
                id=pk,
                status=Listing.Status.ACTIVE,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        contact = get_listing_contact_details(listing)
        if not contact["contact_phone"] and not contact["contact_email"]:
            return Response(
                {"detail": "Seller contact is unavailable"},
                status=status.HTTP_404_NOT_FOUND,
            )

        tracked = not request.user.is_authenticated or request.user.id != listing.user_id
        if tracked:
            Listing.objects.filter(id=pk).update(interest_count=F("interest_count") + 1)

        payload = {
            "contact_name": contact["contact_name"],
            "contact_phone": contact["contact_phone"],
            "contact_email": contact["contact_email"],
            "tracked": tracked,
        }
        return Response(payload, status=status.HTTP_200_OK)
