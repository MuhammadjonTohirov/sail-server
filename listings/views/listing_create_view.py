from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..serializers import ListingCreateSerializer


class ListingCreateView(generics.CreateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
