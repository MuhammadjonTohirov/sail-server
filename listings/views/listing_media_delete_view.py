from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing, ListingMedia


class ListingMediaDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int, media_id: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
            media = ListingMedia.objects.get(id=media_id, listing=listing)
        except (Listing.DoesNotExist, ListingMedia.DoesNotExist):
            return Response({"detail": "Not found"}, status=404)

        media.delete()
        return Response({"status": "deleted"}, status=200)
