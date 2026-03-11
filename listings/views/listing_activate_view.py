from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingActivateView(APIView):
    """Activate a paused listing by setting its status back to active"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Activate a listing",
        description="Reactivate a paused or closed listing owned by the current user.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"status": "activated", "new_status": "active"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
            ),
            OpenApiExample(
                "Invalid status",
                value={
                    "success": False,
                    "data": None,
                    "error": "Can only activate paused or closed listings",
                    "code": 400,
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
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
