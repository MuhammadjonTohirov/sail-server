from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from .push import send_chat_message_notification


logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def send_new_message_notification(self, payload: dict[str, Any]) -> None:
    """
    Placeholder task for dispatching chat message notifications.

    Payload is expected to include:
      - thread_id: UUID string
      - message_id: UUID string
      - recipient_id: int
      - sender_id: int
      - preview: str
    """
    thread_id = payload.get("thread_id")
    message_id = payload.get("message_id")
    recipient_id = payload.get("recipient_id")
    sender_id = payload.get("sender_id")
    preview = payload.get("preview")
    unread_count = payload.get("unread_count", 0)

    logger.info(
        "Dispatching chat message notification | thread=%s recipient=%s sender=%s message=%s preview=%s unread=%s",
        thread_id,
        recipient_id,
        sender_id,
        message_id,
        preview,
        unread_count,
    )

    send_chat_message_notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        thread_id=thread_id,
        message_id=message_id,
        preview=preview,
        unread_count=unread_count,
        extra={k: v for k, v in payload.items() if k not in {"thread_id", "recipient_id", "sender_id", "message_id", "preview", "unread_count"}},
    )

    return None
