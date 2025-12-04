from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingDeleteView(APIView):
    """Delete a listing permanently"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        listing.delete()
        return Response({"status": "deleted"}, status=200)
