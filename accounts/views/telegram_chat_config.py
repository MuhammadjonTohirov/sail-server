"""Telegram chat configuration management views."""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import TelegramChatConfig
from ..serializers import TelegramChatConfigSerializer


logger = logging.getLogger(__name__)


def verify_bot_in_chat(chat_id: int) -> tuple[bool, str]:
    """
    Check if the bot is still a member/admin in the specified chat.
    Returns (is_active, status_string)
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not bot_token:
        return True, "unknown"  # Can't verify without token, assume active

    try:
        # Get chat member info for the bot itself
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getChatMember",
            params={"chat_id": chat_id, "user_id": bot_token.split(":")[0]},
            timeout=10,
        )

        if not resp.ok:
            # If 400/403, bot was likely kicked or chat was deleted
            return False, "kicked"

        data = resp.json()
        if not data.get("ok"):
            return False, "error"

        member_status = data.get("result", {}).get("status", "unknown")
        # Valid statuses: creator, administrator, member, restricted, left, kicked
        is_active = member_status in ("creator", "administrator", "member")
        return is_active, member_status

    except requests.RequestException as e:
        logger.error(f"Error verifying bot in chat {chat_id}: {e}")
        return True, "error"  # Assume active on network error


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

    @extend_schema(
        tags=["telegram"],
        summary="List connected Telegram chats",
        description="Return all Telegram channels and groups connected by the authenticated user.",
        responses={200: TelegramChatConfigSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": [
                        {
                            "id": "uuid",
                            "chat_id": -1001234567890,
                            "chat_type": "channel",
                            "chat_title": "My Channel",
                            "is_active": True,
                            "bot_status": "administrator",
                        }
                    ],
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["telegram"],
        summary="Get connected chat details",
        description="Return details of a specific connected Telegram chat.",
        responses={200: TelegramChatConfigSerializer, 404: None},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["telegram"],
        summary="Disconnect a Telegram chat",
        description="Remove a specific Telegram chat connection. The user would need to re-add the bot to reconnect.",
        responses={200: None, 404: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"detail": "Chat 'My Channel' has been disconnected."},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
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

    @extend_schema(
        tags=["telegram"],
        summary="Disconnect all Telegram chats",
        description="Remove all connected Telegram chats for the authenticated user. Useful for bulk cleanup.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"detail": "Successfully disconnected 3 chat(s)."},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "No chats",
                value={
                    "success": True,
                    "data": {"detail": "No chats to disconnect."},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
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

    @extend_schema(
        tags=["telegram"],
        summary="Get chat statistics",
        description="Return aggregated statistics about connected Telegram chats including counts by type and active status.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "total": 5,
                        "active": 4,
                        "inactive": 1,
                        "by_type": {"channel": 2, "supergroup": 2, "group": 1},
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
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

    @extend_schema(
        tags=["telegram"],
        summary="Verify all connected chats",
        description="Check with the Telegram API whether the bot is still active in each connected chat "
        "and update their is_active and bot_status fields accordingly.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"verified": 3, "deactivated": 1, "errors": 0},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request):
        """
        Verify all connected chats and update their status.

        Checks with Telegram API if the bot is still active in each chat,
        and updates the is_active and bot_status fields accordingly.
        """
        queryset = self.get_queryset()
        results = {"verified": 0, "deactivated": 0, "errors": 0}

        for chat_config in queryset:
            try:
                is_active, bot_status = verify_bot_in_chat(chat_config.chat_id)
                chat_config.bot_status = bot_status
                chat_config.is_active = is_active
                chat_config.last_verified_at = timezone.now()
                chat_config.save(update_fields=["bot_status", "is_active", "last_verified_at", "updated_at"])

                results["verified"] += 1
                if not is_active:
                    results["deactivated"] += 1

            except Exception as e:
                logger.error(f"Error verifying chat {chat_config.chat_id}: {e}")
                results["errors"] += 1

        return Response(results)
