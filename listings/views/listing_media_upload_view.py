from __future__ import annotations

from rest_framework import permissions
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing, ListingMedia
from ..serializers import ListingMediaSerializer


class ListingMediaUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

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
