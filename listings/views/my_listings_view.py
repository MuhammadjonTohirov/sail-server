from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..serializers import ListingSerializer


class MyListingsView(generics.ListAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Listing.objects.filter(user=self.request.user).prefetch_related("media")
