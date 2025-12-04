from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingActivateView(APIView):
    """Activate a paused listing by setting its status back to active"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        if listing.status not in [Listing.Status.PAUSED, Listing.Status.CLOSED]:
            return Response(
                {"detail": "Can only activate paused or closed listings"},
                status=400
            )

        listing.status = Listing.Status.ACTIVE
        listing.refreshed_at = timezone.now()
        listing.save(update_fields=["status", "refreshed_at"])
        return Response({"status": "activated", "new_status": listing.status})
