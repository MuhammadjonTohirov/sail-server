from __future__ import annotations

import uuid

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from listings.models import Listing

from ..models import ChatThread
from ..permissions import IsChatParticipant
from ..serializers import (
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    ChatThreadCreateSerializer,
    ChatThreadSerializer,
)
from ..services import ListingSnapshot, UserSnapshot, append_message, get_or_create_thread, mark_read, set_archive_state, soft_delete_thread


def _snapshot_for_user(user) -> UserSnapshot:
    profile = getattr(user, "profile", None)
    display_name = ""
    avatar_url = ""
    if profile:
        display_name = getattr(profile, "display_name", "") or ""
        avatar_url = getattr(profile, "avatar_url", "") or ""
    if not display_name:
        display_name = user.get_full_name() or user.get_username()
    return UserSnapshot(user_id=user.id, display_name=display_name, avatar_url=avatar_url)


def _snapshot_for_listing(listing: Listing, request) -> ListingSnapshot:
    thumbnail_url = ""
    candidate = None
    prefetched = getattr(listing, "prefetched_media", None)
    if prefetched:
        ordered = sorted(prefetched, key=lambda m: (getattr(m, "order", 0), getattr(m, "id", 0)))
        candidate = ordered[0] if ordered else None
    if not candidate and hasattr(listing, "media"):
        candidate = listing.media.order_by("order", "id").first()
    if candidate and getattr(candidate, "image", None):
        try:
            url = candidate.image.url
            thumbnail_url = url
        except ValueError:
            thumbnail_url = ""

    return ListingSnapshot(
        listing_id=listing.id,
        title=listing.title,
        price_amount=listing.price_amount,
        price_currency=listing.price_currency,
        thumbnail_url=thumbnail_url,
    )


class ChatThreadViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatThreadSerializer
    permission_classes = [IsChatParticipant]
    lookup_field = "id"
    queryset = ChatThread.objects.none()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ChatThread.objects.none()
        qs = (
            ChatThread.objects.filter(participants__user_id=user.id, participants__is_deleted=False)
            .prefetch_related("participants")
            .order_by("-last_message_at", "-updated_at")
            .distinct()
        )

        archived = self.request.query_params.get("archived")
        if archived is not None:
            truthy = {"1", "true", "yes", "on"}
            falsy = {"0", "false", "no", "off"}
            if archived.lower() in truthy:
                qs = qs.filter(participants__user_id=user.id, participants__is_archived=True)
            elif archived.lower() in falsy:
                qs = qs.filter(participants__user_id=user.id, participants__is_archived=False)

        role = self.request.query_params.get("role")
        if role in {"buyer", "seller"}:
            qs = qs.filter(participants__user_id=user.id, participants__role=role)

        my_ads = self.request.query_params.get("my_ads")
        if my_ads and my_ads.lower() in {"1", "true", "yes"}:
            qs = qs.filter(seller_id=user.id)

        unread = self.request.query_params.get("unread")
        if unread and unread.lower() in {"1", "true", "yes"}:
            qs = qs.filter(participants__user_id=user.id, participants__unread_count__gt=0)

        return qs

    @extend_schema(
        tags=["chat"],
        summary="List chat threads",
        description="List all chat threads for the authenticated user with optional filtering.",
        parameters=[
            OpenApiParameter(name="archived", description="Filter by archived status", required=False, type=bool),
            OpenApiParameter(name="role", description="Filter by role (buyer/seller)", required=False, type=str),
            OpenApiParameter(name="my_ads", description="Show only threads for user's own listings", required=False, type=bool),
            OpenApiParameter(name="unread", description="Show only threads with unread messages", required=False, type=bool),
        ],
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": [{"id": "uuid", "buyer_id": 1, "seller_id": 2, "status": "active", "listing": {"listing_id": 10, "title": "iPhone 15"}, "unread_count": 3}], "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["chat"],
        summary="Retrieve a chat thread",
        description="Get details of a specific chat thread by ID.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "buyer_id": 1, "seller_id": 2, "status": "active", "listing": {"listing_id": 10, "title": "iPhone 15"}, "unread_count": 0}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        thread = self.get_object()
        serializer = self.get_serializer(thread)
        return Response(serializer.data)

    @extend_schema(
        tags=["chat"],
        summary="Create or get a chat thread",
        description="Create a new chat thread for a listing, or return existing one. Optionally send an initial message.",
        request=ChatThreadCreateSerializer,
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "buyer_id": 1, "seller_id": 2, "status": "active", "listing": {"listing_id": 10, "title": "iPhone 15"}}, "error": None, "code": 201},
                response_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = ChatThreadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing_id = serializer.validated_data["listing_id"]

        try:
            listing = (
                Listing.objects.select_related("user")
                .prefetch_related(Prefetch("media", to_attr="prefetched_media"))
                .get(pk=listing_id, status=Listing.Status.ACTIVE)
            )
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

        current_user = request.user
        if listing.user_id == current_user.id:
            return Response({"detail": "Cannot start a chat with your own listing."}, status=status.HTTP_400_BAD_REQUEST)

        buyer_snapshot = _snapshot_for_user(current_user)
        seller_snapshot = _snapshot_for_user(listing.user)
        listing_snapshot = _snapshot_for_listing(listing, request)

        thread, created = get_or_create_thread(
            listing=listing_snapshot,
            buyer=buyer_snapshot,
            seller=seller_snapshot,
        )

        message_body = serializer.validated_data.get("message", "")
        attachments = serializer.validated_data.get("attachments", [])
        client_message_id = serializer.validated_data.get("client_message_id", "")
        if message_body or attachments:
            append_message(
                thread=thread,
                sender=buyer_snapshot,
                body=message_body,
                attachments=attachments,
                metadata={},
                client_message_id=client_message_id,
            )

        response_data = self._serialize_thread(thread)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_data, status=status_code)

    def _get_participant(self, thread: ChatThread):
        return thread.participants.filter(user_id=self.request.user.id).first()

    def _serialize_thread(self, thread: ChatThread) -> dict:
        fresh = (
            ChatThread.objects.prefetch_related("participants")
            .filter(pk=thread.pk)
            .first()
        )
        target = fresh or thread
        serializer = self.get_serializer(target)
        return serializer.data

    @extend_schema(
        tags=["chat"],
        summary="Archive a chat thread",
        description="Archive a chat thread for the current user.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "is_archived": True}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        set_archive_state(participant=participant, archived=True)
        return Response(self._serialize_thread(thread))

    @extend_schema(
        tags=["chat"],
        summary="Unarchive a chat thread",
        description="Unarchive a previously archived chat thread.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "is_archived": False}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        set_archive_state(participant=participant, archived=False)
        return Response(self._serialize_thread(thread))

    @extend_schema(
        tags=["chat"],
        summary="Mark thread as read",
        description="Mark messages in a thread as read up to a specific message ID.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "unread_count": 0}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="read", url_name="read")
    def mark_read(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        message_id = request.data.get("message_id")
        if message_id:
            try:
                message_uuid = uuid.UUID(str(message_id))
            except (TypeError, ValueError):
                return Response({"detail": "Invalid UUID for message_id."}, status=status.HTTP_400_BAD_REQUEST)
            if not thread.messages.filter(id=message_uuid).exists():
                return Response({"detail": "Message not found in this thread."}, status=status.HTTP_400_BAD_REQUEST)
            message_id = str(message_uuid)

        mark_read(participant=participant, message_id=message_id)
        return Response(self._serialize_thread(thread))

    @extend_schema(
        tags=["chat"],
        summary="Delete a chat thread",
        description="Soft-delete a chat thread for the current user.",
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        soft_delete_thread(participant=participant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["chat"],
        summary="List messages in a thread",
        description="Get paginated messages for a chat thread with cursor-based pagination.",
        parameters=[
            OpenApiParameter(name="limit", description="Number of messages to return (1-100, default 50)", required=False, type=int),
            OpenApiParameter(name="before", description="Return messages before this datetime (ISO 8601)", required=False, type=str),
            OpenApiParameter(name="after", description="Return messages after this datetime (ISO 8601)", required=False, type=str),
        ],
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"messages": [{"id": "uuid", "sender_id": 1, "body": "Hello!", "created_at": "2025-01-01T00:00:00Z"}], "has_more": False}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_path="messages", url_name="messages")
    def list_messages(self, request, **kwargs):
        thread = self.get_object()
        queryset = thread.messages.all()

        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param else 50
        except (TypeError, ValueError):
            return Response({"detail": "limit must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        limit = max(1, min(limit, 100))

        before_raw = request.query_params.get("before")
        after_raw = request.query_params.get("after")

        def _parse_datetime(value: str | None):
            if not value:
                return None
            parsed = parse_datetime(value)
            if parsed and parsed.tzinfo is None:
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            return parsed

        before_dt = _parse_datetime(before_raw)
        after_dt = _parse_datetime(after_raw)

        if before_raw and not before_dt:
            return Response({"detail": "Invalid datetime format for 'before'."}, status=status.HTTP_400_BAD_REQUEST)
        if after_raw and not after_dt:
            return Response({"detail": "Invalid datetime format for 'after'."}, status=status.HTTP_400_BAD_REQUEST)

        if after_dt:
            queryset = queryset.filter(created_at__gt=after_dt).order_by("created_at", "id")
            messages = list(queryset[:limit])
            has_more = False
        else:
            if before_dt:
                queryset = queryset.filter(created_at__lt=before_dt)
            queryset = queryset.order_by("-created_at", "-id")
            buffered = list(queryset[: limit + 1])
            has_more = len(buffered) > limit
            messages = list(reversed(buffered[:limit]))

        serializer = ChatMessageSerializer(messages, many=True)
        return Response({"messages": serializer.data, "has_more": has_more})

    @extend_schema(
        tags=["chat"],
        summary="Send a message in a thread",
        description="Send a new message in an existing chat thread.",
        request=ChatMessageCreateSerializer,
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"id": "uuid", "sender_id": 1, "body": "Hello!", "created_at": "2025-01-01T00:00:00Z"}, "error": None, "code": 201},
                response_only=True,
            ),
        ],
    )
    @list_messages.mapping.post
    def create_message(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = serializer.validated_data.get("body", "")
        attachments = serializer.validated_data.get("attachments", [])
        metadata = serializer.validated_data.get("metadata", {})
        client_message_id = serializer.validated_data.get("client_message_id", "")

        sender_snapshot = _snapshot_for_user(request.user)
        message = append_message(
            thread=thread,
            sender=sender_snapshot,
            body=body,
            attachments=attachments,
            metadata=metadata,
            client_message_id=client_message_id,
        )

        serialized_message = ChatMessageSerializer(message)
        thread.refresh_from_db()
        return Response(serialized_message.data, status=status.HTTP_201_CREATED)
