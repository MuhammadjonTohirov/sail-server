from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingDeactivateView(APIView):
    """Deactivate a listing by setting its status to paused"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        listing.status = Listing.Status.PAUSED
        listing.save(update_fields=["status"])
        return Response({"status": "deactivated", "new_status": listing.status})
