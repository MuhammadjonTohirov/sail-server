from __future__ import annotations

from typing import Iterable, Sequence

from django.utils import timezone

from .models import ChatMessage, ChatThreadParticipant
from .tasks import send_new_message_notification


def schedule_new_message_notifications(
    *,
    message: ChatMessage,
    participants: Sequence[ChatThreadParticipant] | Iterable[ChatThreadParticipant],
) -> None:
    recipients = [p for p in participants if p.user_id != message.sender_id and not p.is_deleted]
    if not recipients:
        return

    payload_base = {
        "thread_id": str(message.thread_id),
        "message_id": str(message.id),
        "sender_id": message.sender_id,
        "preview": message.body[:120] if message.body else message.last_attachment_caption(),
    }

    now = timezone.now()
    for participant in recipients:
        send_new_message_notification.delay(
            {
                **payload_base,
                "recipient_id": participant.user_id,
                "unread_count": participant.unread_count,
                "queued_at": now.isoformat(),
            }
        )
