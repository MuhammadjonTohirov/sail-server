from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing, ListingMedia


class ListingMediaDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Delete listing media",
        description="Remove a specific media file from a listing.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"status": "deleted"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
            ),
        ],
    )
    def delete(self, request, pk: int, media_id: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
            media = ListingMedia.objects.get(id=media_id, listing=listing)
        except (Listing.DoesNotExist, ListingMedia.DoesNotExist):
            return Response({"detail": "Not found"}, status=404)

        media.delete()
        return Response({"status": "deleted"}, status=200)
