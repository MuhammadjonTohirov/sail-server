from __future__ import annotations

from django.db.models import F
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

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(id=pk, status=Listing.Status.ACTIVE)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Increment the interest count
        Listing.objects.filter(id=pk).update(interest_count=F('interest_count') + 1)

        return Response({"tracked": True}, status=status.HTTP_200_OK)
