from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Listing
from ..serializers import ListingCreateSerializer
from ..tasks import share_listing_to_telegram_task


class ListingCreateView(generics.CreateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        listing = serializer.save()
        
        # Check if telegram sharing was requested
        # The serializer stores this on the instance temporarily
        chat_ids = getattr(listing, "_sharing_telegram_chat_ids", [])
        
        if chat_ids:
            # Trigger Celery task
            share_listing_to_telegram_task.delay(listing.id, chat_ids)
