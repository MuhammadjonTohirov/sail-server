from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import serializers

from .models import ChatMessage, ChatThread, ChatThreadParticipant


class ListingSnapshotSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="listing_id")
    title = serializers.CharField()
    price_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    price_currency = serializers.CharField()
    thumbnail_url = serializers.URLField(allow_blank=True)


class ParticipantSummarySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.URLField(allow_blank=True)


class AttachmentSerializer(serializers.Serializer):
    TYPE_CHOICES = (("image", "Image"), ("file", "File"))

    type = serializers.ChoiceField(choices=TYPE_CHOICES)
    url = serializers.CharField(max_length=2048)
    name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    size = serializers.IntegerField(min_value=0, required=False)
    content_type = serializers.CharField(max_length=255, allow_blank=True, required=False)
    width = serializers.IntegerField(min_value=1, required=False)
    height = serializers.IntegerField(min_value=1, required=False)

    def validate_url(self, value: str) -> str:
        parsed = urlparse(value)
        allowed_prefixes = getattr(settings, "CHAT_ATTACHMENT_ALLOWED_URL_PREFIXES", [])
        if parsed.scheme:
            if allowed_prefixes and not any(value.startswith(prefix) for prefix in allowed_prefixes):
                raise serializers.ValidationError("Attachment URL is not allowed.")
            return value
        if not value.startswith("/"):
            raise serializers.ValidationError("Attachment URL must be absolute or start with '/'.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("type") == "image":
            if attrs.get("width") is not None and attrs["width"] <= 0:
                raise serializers.ValidationError("Image width must be positive.")
            if attrs.get("height") is not None and attrs["height"] <= 0:
                raise serializers.ValidationError("Image height must be positive.")
        return attrs


class ChatThreadSerializer(serializers.ModelSerializer):
    listing = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    last_read_message_id = serializers.SerializerMethodField()
    last_read_at = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            "id",
            "buyer_id",
            "seller_id",
            "status",
            "listing",
            "other_participant",
            "last_message_at",
            "last_message_preview",
            "unread_count",
            "is_archived",
            "last_read_message_id",
            "last_read_at",
            "created_at",
            "updated_at",
        ]

    def _get_current_participant(self, obj: ChatThread) -> ChatThreadParticipant | None:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if hasattr(obj, "_prefetched_objects_cache"):
            participants = obj.participants.all()
        else:
            participants = obj.participants.filter(user_id=user.id)
        for participant in participants:
            if participant.user_id == user.id:
                return participant
        return None

    def get_listing(self, obj: ChatThread) -> Any:
        return {
            "listing_id": obj.listing_id,
            "title": obj.listing_title,
            "price_amount": obj.listing_price_amount,
            "price_currency": obj.listing_price_currency,
            "thumbnail_url": obj.listing_thumbnail_url,
        }

    def get_other_participant(self, obj: ChatThread) -> dict[str, Any] | None:
        request = self.context.get("request")
        user_id = getattr(getattr(request, "user", None), "id", None)
        participants = obj.participants.all()
        for participant in participants:
            if participant.user_id != user_id:
                return {
                    "user_id": participant.user_id,
                    "role": participant.role,
                    "display_name": participant.display_name,
                    "avatar_url": participant.avatar_url,
                }
        return None

    def get_unread_count(self, obj: ChatThread) -> int:
        participant = self._get_current_participant(obj)
        return participant.unread_count if participant else 0

    def get_is_archived(self, obj: ChatThread) -> bool:
        participant = self._get_current_participant(obj)
        return participant.is_archived if participant else False

    def get_last_read_message_id(self, obj: ChatThread) -> str | None:
        participant = self._get_current_participant(obj)
        return str(participant.last_read_message_id) if participant and participant.last_read_message_id else None

    def get_last_read_at(self, obj: ChatThread):
        participant = self._get_current_participant(obj)
        return participant.last_read_at if participant else None


class ChatMessageSerializer(serializers.ModelSerializer):
    is_deleted = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "thread_id",
            "sender_id",
            "sender_display_name",
            "body",
            "attachments",
            "metadata",
            "client_message_id",
            "created_at",
            "edited_at",
            "deleted_at",
            "is_deleted",
        ]
        read_only_fields = fields

    def get_is_deleted(self, obj: ChatMessage) -> bool:
        return obj.deleted_at is not None


class ChatThreadCreateSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    attachments = AttachmentSerializer(required=False, many=True)
    client_message_id = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        message = attrs.get("message") or ""
        attachments = attrs.get("attachments") or []
        max_attachments = getattr(settings, "CHAT_MAX_ATTACHMENTS_PER_MESSAGE", 5)
        if len(attachments) > max_attachments:
            raise serializers.ValidationError(f"Maximum {max_attachments} attachments per message.")
        if not message.strip() and not attachments:
            raise serializers.ValidationError("Provide at least a message or an attachment.")
        if message and len(message.strip()) == 0:
            attrs["message"] = ""
        return attrs


class ChatMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    attachments = AttachmentSerializer(required=False, many=True)
    metadata = serializers.DictField(required=False)
    client_message_id = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        body = attrs.get("body") or ""
        attachments = attrs.get("attachments") or []
        max_attachments = getattr(settings, "CHAT_MAX_ATTACHMENTS_PER_MESSAGE", 5)
        if len(attachments) > max_attachments:
            raise serializers.ValidationError(f"Maximum {max_attachments} attachments per message.")
        if not body.strip() and not attachments:
            raise serializers.ValidationError("Provide at least a message body or attachment.")
        if body and len(body.strip()) == 0:
            attrs["body"] = ""
        return attrs
