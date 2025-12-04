from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing, ListingMedia
from ..serializers import ListingMediaSerializer


class ListingMediaReorderView(APIView):
    """Reorder media for a listing. Expects: {"media_ids": [3, 1, 2]}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        media_ids = request.data.get("media_ids", [])
        if not isinstance(media_ids, list):
            return Response({"detail": "media_ids must be a list"}, status=400)

        # Verify all media belong to this listing
        existing_media = list(listing.media.all())
        existing_ids = {m.id for m in existing_media}

        for media_id in media_ids:
            if media_id not in existing_ids:
                return Response(
                    {"detail": f"Media {media_id} does not belong to listing {pk}"},
                    status=400
                )

        # Update order field for each media
        for order, media_id in enumerate(media_ids):
            ListingMedia.objects.filter(id=media_id, listing=listing).update(order=order)

        # Return updated media list
        updated_media = listing.media.all().order_by("order", "id")
        serializer = ListingMediaSerializer(updated_media, many=True, context={"request": request})
        return Response({"media": serializer.data}, status=200)
