from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import TelegramChatConfig
from ..models import Listing
from ..tasks import share_listing_to_telegram_task


class ListingShareView(APIView):
    """
    Share a listing to specified Telegram chats.
    Expects body: { "telegram_chat_ids": [123, 456] }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        chat_ids = request.data.get("telegram_chat_ids", [])
        
        if not chat_ids or not isinstance(chat_ids, list):
            return Response(
                {"error": "telegram_chat_ids list is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate ownership of chat configs
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
