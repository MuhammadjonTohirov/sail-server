import logging
import requests
from django.conf import settings
from django.urls import reverse
from .models import Listing

logger = logging.getLogger(__name__)

class TelegramSharingService:
    @staticmethod
    def share_listing(listing_id: int, chat_ids: list[int]):
        """
        Share a listing to multiple Telegram chats.
        """
        try:
            listing = Listing.objects.select_related("category", "location", "currency").get(id=listing_id)
        except Listing.DoesNotExist:
            logger.error(f"Listing {listing_id} not found for Telegram sharing")
            return

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured, skipping sharing")
            return

        # Construct message
        # TODO: Use a proper frontend URL builder
        frontend_url = settings.WEB_BASE_URL.rstrip("/") if hasattr(settings, "WEB_BASE_URL") else "https://sail.uz"
        listing_url = f"{frontend_url}/l/{listing.id}"
        
        price_text = f"{listing.price_amount:, .0f} {listing.price_currency}" if listing.price_amount else "Договорная"
        
        # Hashtags from category hierarchy
        hashtags = []
        cat = listing.category
        while cat:
            slug = cat.slug.replace("-", "_")
            hashtags.append(f"#{slug}")
            cat = cat.parent
        hashtags_str = " ".join(hashtags)

        caption = (
            f"<b>{listing.title}</b>\n\n"
            f"💰 {price_text}\n"
            f"📍 {listing.location.name if listing.location else 'Uzbekistan'}\n\n"
            f"{listing.description[:200]}{'...' if len(listing.description) > 200 else ''}\n\n"
            f"{hashtags_str}\n\n"
            f"👉 <a href='{listing_url}'>Посмотреть объявление</a>"
        )

        # Get first image if available
        first_image = listing.media.filter(type="image").order_by("order").first()
        
        for chat_id in chat_ids:
            try:
                if first_image:
                    # Send photo
                    # We use the absolute file path or URL depending on storage
                    # For S3/Cloud, image.url is a full URL. For local, it might be relative.
                    image_url = first_image.image.url
                    if not image_url.startswith("http"):
                        # If local dev and relative, try to construct full URL or send file
                        # For simplicity in this MVP, we assume public URL or accessible path
                        # If using local storage, we might need to open the file
                        pass 

                    # Sending by URL is easiest if public
                    # If local, we might need to send as multipart/form-data
                    
                    # Let's try sending by URL first (works for S3)
                    if image_url.startswith("http"):
                        data = {
                            "chat_id": chat_id,
                            "caption": caption,
                            "parse_mode": "HTML",
                            "photo": image_url
                        }
                        resp = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", data=data, timeout=10)
                    else:
                        # Local file fallback
                        with open(first_image.image.path, "rb") as f:
                            files = {"photo": f}
                            data = {
                                "chat_id": chat_id,
                                "caption": caption,
                                "parse_mode": "HTML"
                            }
                            resp = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", data=data, files=files, timeout=10)
                else:
                    # Send text only
                    data = {
                        "chat_id": chat_id,
                        "text": caption,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False
                    }
                    resp = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=data, timeout=10)

                if not resp.ok:
                    logger.error(f"Failed to send to Telegram chat {chat_id}: {resp.text}")
                else:
                    logger.info(f"Successfully shared listing {listing_id} to chat {chat_id}")

            except Exception as e:
                logger.error(f"Error sending to Telegram chat {chat_id}: {e}")