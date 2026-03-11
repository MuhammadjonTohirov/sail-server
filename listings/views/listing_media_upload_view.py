from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing, ListingMedia
from ..serializers import ListingMediaSerializer


class ListingMediaUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Upload listing media",
        description="Upload an image file for a listing. The file should be sent as multipart form data.",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}, "required": ["file"]}},
        responses={201: ListingMediaSerializer},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"id": 1, "image_url": "/media/listings/photo.jpg", "order": 0},
                    "error": None,
                    "code": 201,
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

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded"}, status=400)

        media = ListingMedia(listing=listing, image=file_obj)
        media.save()
        serializer = ListingMediaSerializer(media, context={"request": request})
        return Response(serializer.data, status=201)
