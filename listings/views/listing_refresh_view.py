from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Refresh (bump) a listing",
        description="Bump a listing to the top of search results by updating its refreshed_at timestamp.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"status": "refreshed", "refreshed_at": "2026-03-11T12:00:00Z"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        listing.refreshed_at = timezone.now()
        listing.save(update_fields=["refreshed_at"])
        return Response({"status": "refreshed", "refreshed_at": listing.refreshed_at})
