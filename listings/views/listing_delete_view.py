from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing


class ListingDeleteView(APIView):
    """Delete a listing permanently"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Delete a listing",
        description="Permanently delete a listing owned by the current user.",
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
    def delete(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        listing.delete()
        return Response({"status": "deleted"}, status=200)
