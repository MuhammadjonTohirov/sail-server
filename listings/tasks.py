from celery import shared_task
from .telegram_sharing import TelegramSharingService

@shared_task
def share_listing_to_telegram_task(listing_id: int, chat_ids: list[int]):
    """
    Celery task to share a listing to Telegram channels asynchronously.
    """
    TelegramSharingService.share_listing(listing_id, chat_ids)
