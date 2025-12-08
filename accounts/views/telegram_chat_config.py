"""Telegram chat configuration management views."""
from __future__ import annotations

import logging

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import TelegramChatConfig
from ..serializers import TelegramChatConfigSerializer


logger = logging.getLogger(__name__)


class TelegramChatConfigViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing user's Telegram chat configurations.

    list: Get all connected chats for the authenticated user
    retrieve: Get details of a specific chat
    destroy: Remove/disconnect a chat
    disconnect_all: Remove all chats (bulk operation)
    stats: Get chat statistics
    """

    serializer_class = TelegramChatConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        """Filter chats by authenticated user's profile."""
        return (
            TelegramChatConfig.objects.filter(profile__user=self.request.user)
            .select_related("profile")
            .order_by("-created_at")
        )

    def destroy(self, request, *args, **kwargs):
        """
        Disconnect/remove a specific chat.

        Note: This deletes the record. The user would need to re-add
        the bot to reconnect the chat.
        """
        instance = self.get_object()
        chat_title = instance.chat_title or f"Chat {instance.chat_id}"

        self.perform_destroy(instance)

        logger.info(
            f"User {request.user.id} disconnected Telegram chat: " f"{chat_title} (chat_id={instance.chat_id})"
        )

        return Response({"detail": f"Chat '{chat_title}' has been disconnected."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="disconnect-all")
    def disconnect_all(self, request):
        """
        Disconnect all chats for the authenticated user.

        Useful for bulk cleanup or privacy management.
        """
        queryset = self.get_queryset()
        count = queryset.count()

        if count == 0:
            return Response({"detail": "No chats to disconnect."}, status=status.HTTP_200_OK)

        queryset.delete()

        logger.info(f"User {request.user.id} disconnected all {count} Telegram chats")

        return Response({"detail": f"Successfully disconnected {count} chat(s)."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        Get statistics about connected chats.

        Returns counts by chat type and active status.
        """
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "active": queryset.filter(is_active=True).count(),
            "inactive": queryset.filter(is_active=False).count(),
            "by_type": {
                "channel": queryset.filter(chat_type="channel").count(),
                "supergroup": queryset.filter(chat_type="supergroup").count(),
                "group": queryset.filter(chat_type="group").count(),
            },
        }

        return Response(stats)
