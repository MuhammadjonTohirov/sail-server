from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

import requests
from celery import shared_task
from django.conf import settings

from .models import SavedSearch
from .utils import count_new_items_for_saved_search

logger = logging.getLogger(__name__)


def send_telegram_notification(telegram_id: int, message: str) -> bool:
    """Send a notification message to a user via Telegram."""
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if not resp.ok:
            logger.error(f"Failed to send Telegram notification to {telegram_id}: {resp.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram notification to {telegram_id}: {e}")
        return False


@shared_task(name="savedsearches.run_daily_notifications")
def task_run_daily_saved_search_notifications():
    """
    Send daily Telegram notifications to users about new items in their saved searches.
    This task should be scheduled to run once daily (e.g., via Celery Beat).
    """
    from accounts.models import Profile

    processed = 0
    notifications_sent = 0

    # Get all daily saved searches for users with Telegram connected
    saved_searches = SavedSearch.objects.filter(
        is_active=True,
        frequency=SavedSearch.Frequency.DAILY,
        user__profile__telegram_id__isnull=False,
    ).select_related("user__profile")

    for saved_search in saved_searches.iterator():
        try:
            # Count new items since last notification
            new_count = count_new_items_for_saved_search(saved_search)

            if new_count > 0:
                profile = saved_search.user.profile
                telegram_id = profile.telegram_id

                if telegram_id:
                    # Build notification message
                    frontend_url = getattr(settings, "WEB_BASE_URL", "https://sail.uz").rstrip("/")
                    search_url = f"{frontend_url}/favorites"

                    # Pluralize based on count
                    if new_count == 1:
                        items_text = "новое объявление"
                    elif 2 <= new_count <= 4:
                        items_text = "новых объявления"
                    else:
                        items_text = "новых объявлений"

                    message = (
                        f"🔔 <b>Новые объявления по вашему запросу</b>\n\n"
                        f"📋 <b>{saved_search.title}</b>\n"
                        f"📊 Найдено: {new_count} {items_text}\n\n"
                        f"👉 <a href='{search_url}'>Посмотреть результаты</a>"
                    )

                    if send_telegram_notification(telegram_id, message):
                        notifications_sent += 1
                        saved_search.last_sent_at = datetime.now(dt_timezone.utc)
                        saved_search.save(update_fields=["last_sent_at"])

            processed += 1

        except Exception as e:
            logger.error(f"Error processing saved search {saved_search.id}: {e}")
            continue

    return {
        "status": "ok",
        "processed": processed,
        "notifications_sent": notifications_sent,
    }


@shared_task(name="savedsearches.run")
def task_run_saved_searches():
    """Legacy task - runs all saved searches (without notifications)."""
    from searchapp.views.opensearch_client import get_client
    from searchapp.views.index import index_name

    client = get_client()
    if not client:
        return {"status": "skipped", "reason": "no-opensearch"}
    processed = 0
    for s in SavedSearch.objects.filter(is_active=True).iterator():
        q = s.query or {}
        body = q.get("body") or {"query": {"bool": {}}}
        client.search(index=index_name(), body=body)
        s.last_sent_at = datetime.now(dt_timezone.utc)
        s.save(update_fields=["last_sent_at"])
        processed += 1
    return {"status": "ok", "processed": processed}

