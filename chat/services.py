from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Tuple

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import ChatMessage, ChatThread, ChatThreadParticipant
from .notifications import schedule_new_message_notifications


@dataclass(slots=True, frozen=True)
class ListingSnapshot:
    listing_id: int
    title: str = ""
    price_amount: Decimal | None = None
    price_currency: str = ""
    thumbnail_url: str = ""


@dataclass(slots=True, frozen=True)
class UserSnapshot:
    user_id: int
    display_name: str = ""
    avatar_url: str = ""


def _ensure_participant(
    *,
    thread: ChatThread,
    snapshot: UserSnapshot,
    role: ChatThreadParticipant.Role,
) -> ChatThreadParticipant:
    participant, _ = ChatThreadParticipant.objects.get_or_create(
        thread=thread,
        user_id=snapshot.user_id,
        defaults={
            "role": role,
            "display_name": snapshot.display_name,
            "avatar_url": snapshot.avatar_url,
        },
    )
    # Keep lightweight profile info fresh
    needs_update = False
    update_fields: list[str] = []
    if participant.display_name != snapshot.display_name:
        participant.display_name = snapshot.display_name
        update_fields.append("display_name")
        needs_update = True
    if participant.avatar_url != snapshot.avatar_url:
        participant.avatar_url = snapshot.avatar_url
        update_fields.append("avatar_url")
        needs_update = True
    if participant.role != role:
        participant.role = role
        update_fields.append("role")
        needs_update = True
    if participant.is_deleted:
        participant.is_deleted = False
        update_fields.append("is_deleted")
        needs_update = True
    if needs_update:
        update_fields.append("updated_at")
        participant.save(update_fields=update_fields)
    return participant


@transaction.atomic
def get_or_create_thread(
    *,
    listing: ListingSnapshot,
    buyer: UserSnapshot,
    seller: UserSnapshot,
) -> Tuple[ChatThread, bool]:
    thread, created = ChatThread.objects.select_for_update().get_or_create(
        buyer_id=buyer.user_id,
        listing_id=listing.listing_id,
        defaults={
            "seller_id": seller.user_id,
            "listing_title": listing.title,
            "listing_price_amount": listing.price_amount,
            "listing_price_currency": listing.price_currency,
            "listing_thumbnail_url": listing.thumbnail_url,
        },
    )

    # Refresh listing snapshot if details changed (e.g., title update)
    listing_fields_to_update: list[str] = []
    if thread.seller_id != seller.user_id:
        thread.seller_id = seller.user_id
        listing_fields_to_update.append("seller_id")
    if thread.listing_title != listing.title:
        thread.listing_title = listing.title
        listing_fields_to_update.append("listing_title")
    if thread.listing_price_amount != listing.price_amount:
        thread.listing_price_amount = listing.price_amount
        listing_fields_to_update.append("listing_price_amount")
    if thread.listing_price_currency != listing.price_currency:
        thread.listing_price_currency = listing.price_currency
        listing_fields_to_update.append("listing_price_currency")
    if thread.listing_thumbnail_url != listing.thumbnail_url:
        thread.listing_thumbnail_url = listing.thumbnail_url or ""
        listing_fields_to_update.append("listing_thumbnail_url")

    if listing_fields_to_update:
        listing_fields_to_update.append("updated_at")
        thread.save(update_fields=listing_fields_to_update)

    _ensure_participant(thread=thread, snapshot=buyer, role=ChatThreadParticipant.Role.BUYER)
    _ensure_participant(thread=thread, snapshot=seller, role=ChatThreadParticipant.Role.SELLER)

    return thread, created


@transaction.atomic
def append_message(
    *,
    thread: ChatThread,
    sender: UserSnapshot,
    body: str,
    attachments: Iterable[dict] | None = None,
    metadata: dict | None = None,
    client_message_id: str = "",
) -> ChatMessage:
    body = (body or "").strip()
    attachments = list(attachments or [])
    metadata = metadata or {}

    message = ChatMessage.objects.create(
        thread=thread,
        sender_id=sender.user_id,
        sender_display_name=sender.display_name,
        body=body,
        attachments=attachments,
        metadata=metadata,
        client_message_id=client_message_id,
    )

    # Update thread preview and timestamp
    preview = message.body or message.last_attachment_caption()
    thread.touch(preview=preview or "[attachment]", at=message.created_at)

    # Ensure sender participant info is current and increment unread for the other side
    sender_participant = _ensure_participant(
        thread=thread,
        snapshot=sender,
        role=ChatThreadParticipant.Role.BUYER if sender.user_id == thread.buyer_id else ChatThreadParticipant.Role.SELLER,
    )
    sender_participant.last_read_message_id = message.id
    sender_participant.last_read_at = message.created_at
    sender_participant.unread_count = 0
    sender_participant.save(
        update_fields=["last_read_message_id", "last_read_at", "unread_count", "updated_at"]
    )

    # Increment unread count for all other participants
    now = timezone.now()
    ChatThreadParticipant.objects.filter(thread=thread).exclude(user_id=sender.user_id).update(
        unread_count=F("unread_count") + 1,
        is_deleted=False,
        updated_at=now,
    )

    recipients = list(
        ChatThreadParticipant.objects.filter(thread=thread).exclude(user_id=sender.user_id)
    )
    schedule_new_message_notifications(message=message, participants=recipients)

    return message


def mark_read(*, participant: ChatThreadParticipant, message_id: str | None = None) -> None:
    message_uuid = uuid.UUID(str(message_id)) if message_id else None
    participant.mark_read(message_id=message_uuid)


def set_archive_state(*, participant: ChatThreadParticipant, archived: bool) -> ChatThreadParticipant:
    if participant.is_archived != archived:
        participant.is_archived = archived
        participant.save(update_fields=["is_archived", "updated_at"])
    return participant


def soft_delete_thread(*, participant: ChatThreadParticipant) -> None:
    if not participant.is_deleted:
        participant.is_deleted = True
        participant.save(update_fields=["is_deleted", "updated_at"])
