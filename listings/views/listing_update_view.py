from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..permissions import IsOwnerOrReadOnly
from ..serializers import ListingUpdateSerializer


class ListingUpdateView(generics.UpdateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
