from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        listing.refreshed_at = timezone.now()
        listing.save(update_fields=["refreshed_at"])
        return Response({"status": "refreshed", "refreshed_at": listing.refreshed_at})
