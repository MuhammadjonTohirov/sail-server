from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..serializers import ListingSerializer


class ListingDetailView(generics.RetrieveAPIView):
    queryset = Listing.objects.select_related("category", "location", "user").prefetch_related("media")
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]
