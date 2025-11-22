from __future__ import annotations

from rest_framework import permissions

from .models import ChatMessage, ChatThread


class IsChatParticipant(permissions.BasePermission):
    """
    Ensures the requesting user belongs to the chat thread (and the thread isn't deleted for them).
    """

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return False
        if isinstance(obj, ChatThread):
            thread = obj
        elif isinstance(obj, ChatMessage):
            thread = obj.thread
        else:
            thread = getattr(obj, "thread", None)
            if thread is None:
                return False
        return thread.participants.filter(user_id=user_id, is_deleted=False).exists()
