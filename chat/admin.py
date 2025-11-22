from django.contrib import admin

from .models import ChatMessage, ChatThread, ChatThreadParticipant


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "listing_id", "buyer_id", "seller_id", "status", "last_message_at")
    list_filter = ("status",)
    search_fields = ("id", "listing_title", "buyer_id", "seller_id")
    ordering = ("-last_message_at",)


@admin.register(ChatThreadParticipant)
class ChatThreadParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "user_id", "role", "is_archived", "is_deleted", "unread_count")
    list_filter = ("role", "is_archived", "is_deleted")
    search_fields = ("thread__id", "user_id")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "sender_id", "created_at", "deleted_at")
    search_fields = ("id", "thread__id", "sender_id", "body")
    list_filter = ("deleted_at",)
