from __future__ import annotations

import mimetypes
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing

from .models import ChatThread
from .permissions import IsChatParticipant
from .serializers import (
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    ChatThreadCreateSerializer,
    ChatThreadSerializer,
)
from .services import ListingSnapshot, UserSnapshot, append_message, get_or_create_thread, mark_read, set_archive_state, soft_delete_thread


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
            if request is not None:
                try:
                    thumbnail_url = request.build_absolute_uri(url)
                except Exception:
                    thumbnail_url = url
            else:
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

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        thread = self.get_object()
        serializer = self.get_serializer(thread)
        return Response(serializer.data)

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

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        set_archive_state(participant=participant, archived=True)
        return Response(self._serialize_thread(thread))

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        set_archive_state(participant=participant, archived=False)
        return Response(self._serialize_thread(thread))

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
                return Response({"message_id": "Invalid UUID."}, status=status.HTTP_400_BAD_REQUEST)
            if not thread.messages.filter(id=message_uuid).exists():
                return Response({"message_id": "Message not found in this thread."}, status=status.HTTP_400_BAD_REQUEST)
            message_id = str(message_uuid)

        mark_read(participant=participant, message_id=message_id)
        return Response(self._serialize_thread(thread))

    def destroy(self, request, *args, **kwargs):
        thread = self.get_object()
        participant = self._get_participant(thread)
        if not participant:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        soft_delete_thread(participant=participant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="messages", url_name="messages")
    def list_messages(self, request, **kwargs):
        thread = self.get_object()
        queryset = thread.messages.all()

        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param else 50
        except (TypeError, ValueError):
            return Response({"limit": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
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
            return Response({"before": "Invalid datetime format."}, status=status.HTTP_400_BAD_REQUEST)
        if after_raw and not after_dt:
            return Response({"after": "Invalid datetime format."}, status=status.HTTP_400_BAD_REQUEST)

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


class ChatAttachmentUploadView(APIView):
    parser_classes = (MultiPartParser,)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id: uuid.UUID):
        try:
            thread = ChatThread.objects.prefetch_related("participants").get(id=id)
        except ChatThread.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not thread.participants.filter(user_id=request.user.id, is_deleted=False).exists():
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        filename = os.path.basename(file_obj.name) or "attachment"
        storage_path = os.path.join("chat_attachments", str(thread.id), f"{uuid.uuid4().hex}_{filename}")
        saved_path = default_storage.save(storage_path, file_obj)

        if settings.MEDIA_URL.startswith("http://") or settings.MEDIA_URL.startswith("https://"):
            base = settings.MEDIA_URL.rstrip("/")
            public_url = f"{base}/{saved_path}"
        else:
            public_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

        content_type = file_obj.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        attachment_type = "image" if content_type.startswith("image/") else "file"

        payload = {
            "type": attachment_type,
            "url": public_url,
            "name": filename,
            "size": file_obj.size,
            "content_type": content_type,
        }
        return Response(payload, status=status.HTTP_201_CREATED)
