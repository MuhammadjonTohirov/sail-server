from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def send_chat_message_notification(
    *,
    recipient_id: int,
    sender_id: int,
    thread_id: str,
    message_id: str,
    preview: str,
    unread_count: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Hook for integrating push notifications (FCM, APNs, etc.).

    This stub just logs that work remains so you can wire in Firebase (or any
    other provider) later without changing the callsites.
    """
    payload = {
        "recipient_id": recipient_id,
        "sender_id": sender_id,
        "thread_id": thread_id,
        "message_id": message_id,
        "preview": preview,
        "unread_count": unread_count,
        **(extra or {}),
    }
    logger.info("TODO push integration pending | payload=%s", payload)
