from __future__ import annotations

import uuid
from datetime import datetime

from django.db import models
from django.utils import timezone


class ChatThread(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_id = models.BigIntegerField()
    seller_id = models.BigIntegerField()
    listing_id = models.BigIntegerField()
    listing_title = models.CharField(max_length=255, blank=True, default="")
    listing_price_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    listing_price_currency = models.CharField(max_length=3, blank=True, default="")
    listing_thumbnail_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=400, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["buyer_id"]),
            models.Index(fields=["seller_id"]),
            models.Index(fields=["listing_id"]),
            models.Index(fields=["status", "updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["buyer_id", "listing_id"], name="uniq_chat_thread_buyer_listing"),
        ]

    def touch(self, *, preview: str, at: datetime | None = None) -> None:
        """Update cached preview fields after a new message."""
        self.last_message_at = at or timezone.now()
        self.last_message_preview = preview[:400]
        self.save(update_fields=["last_message_at", "last_message_preview", "updated_at"])


class ChatThreadParticipant(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="participants")
    user_id = models.BigIntegerField()
    role = models.CharField(max_length=16, choices=Role.choices)
    display_name = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    unread_count = models.PositiveIntegerField(default=0)
    last_read_message_id = models.UUIDField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "is_deleted"]),
            models.Index(fields=["thread", "role"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["thread", "user_id"], name="uniq_chat_participant_per_thread"),
        ]

    def mark_read(self, message_id: uuid.UUID | None, read_at: datetime | None = None) -> None:
        self.last_read_message_id = message_id
        self.last_read_at = read_at or timezone.now()
        self.unread_count = 0
        self.save(update_fields=["last_read_message_id", "last_read_at", "unread_count", "updated_at"])


class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    sender_id = models.BigIntegerField()
    sender_display_name = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    attachments = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    client_message_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["sender_id"]),
        ]

    def soft_delete(self) -> None:
        if self.deleted_at:
            return
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def last_attachment_caption(self) -> str:
        if not self.attachments:
            return ""
        attachment = self.attachments[0] if isinstance(self.attachments, list) and self.attachments else {}
        return attachment.get("name") or attachment.get("url") or "[attachment]"

# Create your models here.
