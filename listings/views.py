from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import Listing, ListingMedia
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    ListingCreateSerializer,
    ListingMediaSerializer,
    ListingSerializer,
    ListingUpdateSerializer,
)
from .tasks import share_listing_to_telegram_task


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == "create":
            return ListingCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ListingUpdateSerializer
        return ListingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            # Filter for active listings only
            qs = qs.filter(status=Listing.Status.ACTIVE)
            
            # Filter by user if requested
            user_id = self.request.query_params.get("user_id")
            if user_id:
                qs = qs.filter(user_id=user_id)
                
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        """
        Share the listing to specified Telegram chats.
        Expects body: { "telegram_chat_ids": [123, 456] }
        """
        listing = self.get_object()
        chat_ids = request.data.get("telegram_chat_ids", [])
        
        if not chat_ids or not isinstance(chat_ids, list):
            return Response(
                {"error": "telegram_chat_ids list is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate ownership of chat configs
        from accounts.models import TelegramChatConfig
        valid_chats = TelegramChatConfig.objects.filter(
            profile__user=request.user, 
            chat_id__in=chat_ids, 
            is_active=True
        ).values_list("chat_id", flat=True)
        
        valid_chat_ids = list(valid_chats)
        if not valid_chat_ids:
             return Response(
                {"error": "No valid active Telegram chats found for this user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trigger task immediately
        share_listing_to_telegram_task.delay(listing.id, valid_chat_ids)
        
        return Response({
            "status": "sharing_started",
            "chat_ids": valid_chat_ids
        })

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_media(self, request, pk=None):
        listing = self.get_object()
        if listing.media.count() >= 10:
            return Response(
                {"error": "Maximum 10 images allowed per listing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingMediaSerializer(data=request.data)
        if serializer.is_valid():
            # Calculate order
            last_media = listing.media.order_by("-order").first()
            order = (last_media.order + 1) if last_media else 0
            
            serializer.save(listing=listing, order=order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reorder_media(self, request, pk=None):
        listing = self.get_object()
        order_map = request.data.get("order", {})  # {media_id: new_order}
        
        for media in listing.media.all():
            if str(media.id) in order_map:
                media.order = order_map[str(media.id)]
                media.save()
                
        return Response({"status": "reordered"})

    @action(detail=True, methods=["delete"])
    def delete_media(self, request, pk=None):
        listing = self.get_object()
        media_id = request.query_params.get("media_id")
        if not media_id:
            return Response({"error": "media_id required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            media = listing.media.get(id=media_id)
            media.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ListingMedia.DoesNotExist:
            return Response({"error": "Media not found"}, status=status.HTTP_404_NOT_FOUND)
            
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        listing = self.get_object()
        listing.status = Listing.Status.INACTIVE
        listing.save()
        return Response({"status": "deactivated"})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        listing = self.get_object()
        listing.status = Listing.Status.ACTIVE
        listing.save()
        return Response({"status": "activated"})
