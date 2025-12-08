"""Telegram Bot webhook handler for channel/group auto-connect."""
from __future__ import annotations

import logging
import requests

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile, TelegramChatConfig


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(APIView):
    """
    Handle Telegram Bot webhook updates.

    Primary use case: Auto-connect user's Telegram channels/groups when they add
    the bot as an administrator.

    Webhook URL: /api/v1/webhooks/telegram
    """

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        """
        Process incoming Telegram webhook update.

        Expected update types:
        - my_chat_member: Bot added/removed from channel/group

        Update structure:
        {
            "update_id": 123456789,
            "my_chat_member": {
                "chat": {
                    "id": -1001234567890,
                    "title": "My Channel",
                    "username": "mychannel",
                    "type": "channel"
                },
                "from": {
                    "id": 123456789,
                    "is_bot": false,
                    "first_name": "John"
                },
                "date": 1234567890,
                "old_chat_member": {
                    "status": "left",
                    "user": {"id": BOT_ID, "is_bot": true}
                },
                "new_chat_member": {
                    "status": "administrator",
                    "user": {"id": BOT_ID, "is_bot": true}
                }
            }
        }
        """

        # Step 1: Validate and parse JSON
        try:
            update = request.data
            if not isinstance(update, dict):
                logger.warning(f"Invalid webhook payload type: {type(update)}")
                return Response({"ok": False, "error": "Invalid payload"}, status=400)
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            return Response({"ok": False, "error": "Invalid JSON"}, status=400)

        # Step 2: Optional security validation
        if not self._verify_telegram_webhook(request):
            logger.warning(f"Unauthorized webhook attempt from IP: {request.META.get('REMOTE_ADDR')}")
            return Response({"ok": False, "error": "Unauthorized"}, status=403)

        # Step 3: Extract updates
        my_chat_member = update.get("my_chat_member")
        channel_post = update.get("channel_post")
        message = update.get("message")

        # Step 4: Process the update
        try:
            if my_chat_member:
                self._process_chat_member_update(my_chat_member, request)
            elif channel_post:
                self._process_chat_message_update(channel_post)
            elif message:
                self._process_chat_message_update(message)
            
            return Response({"ok": True}, status=200)
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}", exc_info=True)
            # Return 200 to Telegram to prevent retries
            return Response({"ok": True}, status=200)

    def _process_chat_message_update(self, message: dict):
        """Process channel_post or message to update chat info (title, username, photo)."""
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return

        # Find all configs for this chat (could be multiple users admining same chat)
        configs = TelegramChatConfig.objects.filter(chat_id=chat_id)
        if not configs.exists():
            return

        # 1. Passive update of title/username from the chat object header
        new_title = chat.get("title")
        new_username = chat.get("username", "")  # Default to empty string if None

        for config in configs:
            updated_fields = []
            
            if new_title and config.chat_title != new_title:
                config.chat_title = new_title
                updated_fields.append("chat_title")
            
            if new_username is not None and config.chat_username != new_username:
                config.chat_username = new_username
                updated_fields.append("chat_username")
            
            if updated_fields:
                config.save(update_fields=updated_fields + ["updated_at"])
                logger.info(f"Updated chat info for {chat_id} (profile {config.profile_id}): {updated_fields}")

        # 2. Handle Service Messages for Photo Updates
        
        # New Chat Photo
        new_photo = message.get("new_chat_photo")  # List of PhotoSize
        if new_photo:
            # Get largest photo
            largest = sorted(new_photo, key=lambda x: x.get("file_size", 0))[-1]
            file_id = largest.get("file_id")
            
            photo_file = self._download_chat_photo(file_id)
            if photo_file:
                for config in configs:
                    config.chat_photo.save(photo_file.name, photo_file, save=False)
                    config.save(update_fields=["chat_photo", "updated_at"])
                logger.info(f"Updated chat photo for {chat_id} from service message")

        # Delete Chat Photo
        if message.get("delete_chat_photo"):
            for config in configs:
                config.chat_photo = None
                config.save(update_fields=["chat_photo", "updated_at"])
            logger.info(f"Deleted chat photo for {chat_id} from service message")

        # Note: 'new_chat_title' service message is handled by the passive update above

    def _fetch_telegram_chat_details(self, chat_id: int) -> dict:
        """Fetch full chat details from Telegram API."""
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            return {}

        try:
            response = requests.get(
                f"https://api.telegram.org/bot{bot_token}/getChat",
                params={"chat_id": chat_id},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data.get("result", {})
        except Exception as e:
            logger.error(f"Failed to fetch chat details for {chat_id}: {e}")

        return {}

    def _process_chat_member_update(self, update: dict, request):
        """Process my_chat_member update."""

        # Extract data
        chat = update.get("chat", {})
        from_user = update.get("from", {})
        new_member = update.get("new_chat_member", {})
        old_member = update.get("old_chat_member", {})

        chat_id = chat.get("id")
        chat_type = chat.get("type", "")
        chat_title = chat.get("title", "")
        chat_username = chat.get("username", "")

        user_telegram_id = from_user.get("id")
        new_status = new_member.get("status", "")
        old_status = old_member.get("status", "")

        # Validate required fields
        if not all([chat_id, user_telegram_id, new_status]):
            logger.warning(f"Missing required fields in my_chat_member update: {update}")
            return

        # Only process channel/supergroup/group types
        if chat_type not in ["channel", "supergroup", "group"]:
            logger.info(f"Ignoring chat type '{chat_type}' (chat_id={chat_id})")
            return

        logger.info(
            f"Processing my_chat_member: user_telegram_id={user_telegram_id}, "
            f"chat_id={chat_id}, old_status={old_status}, new_status={new_status}"
        )

        # Find user by telegram_id
        try:
            profile = Profile.objects.select_related("user").get(telegram_id=user_telegram_id)
        except Profile.DoesNotExist:
            logger.warning(
                f"User with telegram_id={user_telegram_id} not found in database. "
                f"Cannot auto-connect chat {chat_id}."
            )
            return

        # Process based on new status
        if new_status in ["administrator", "member"]:
            # Fetch full chat details to get the photo
            chat_details = self._fetch_telegram_chat_details(chat_id)

            # Use details from getChat if available, fallback to webhook data
            final_title = chat_details.get("title", chat_title)
            final_username = chat_details.get("username", chat_username)

            photo_file = None
            photo_data = chat_details.get("photo", {})
            big_file_id = photo_data.get("big_file_id")
            if big_file_id:
                photo_file = self._download_chat_photo(big_file_id)

            self._handle_bot_added(
                profile, chat_id, chat_type, final_title, final_username, new_status, photo_file
            )
        elif new_status in ["left", "kicked"]:
            # Bot removed or kicked
            self._handle_bot_removed(profile, chat_id, new_status)
        else:
            logger.info(f"Ignoring status '{new_status}' for chat_id={chat_id}")

    def _handle_bot_added(
        self,
        profile: Profile,
        chat_id: int,
        chat_type: str,
        chat_title: str,
        chat_username: str,
        status: str,
        photo_file: ContentFile | None = None,
    ):
        """Handle bot being added to a channel/group."""

        with transaction.atomic():
            channel_config, created = TelegramChatConfig.objects.get_or_create(
                profile=profile,
                chat_id=chat_id,
                defaults={
                    "chat_type": chat_type,
                    "chat_title": chat_title,
                    "chat_username": chat_username,
                    "is_active": True,
                    "bot_status": status,
                    "last_verified_at": timezone.now(),
                },
            )

            if created:
                if photo_file:
                    channel_config.chat_photo.save(photo_file.name, photo_file, save=False)
                    channel_config.save()

                logger.info(
                    f"Created new chat config: profile_id={profile.id}, chat_id={chat_id}, " f"title='{chat_title}'"
                )
            else:
                # Update existing record
                updated_fields = []

                if channel_config.chat_title != chat_title:
                    channel_config.chat_title = chat_title
                    updated_fields.append("chat_title")

                if channel_config.chat_username != chat_username:
                    channel_config.chat_username = chat_username
                    updated_fields.append("chat_username")

                if channel_config.bot_status != status:
                    channel_config.bot_status = status
                    updated_fields.append("bot_status")

                if not channel_config.is_active:
                    channel_config.is_active = True
                    updated_fields.append("is_active")

                if photo_file:
                    channel_config.chat_photo.save(photo_file.name, photo_file, save=False)
                    updated_fields.append("chat_photo")

                channel_config.last_verified_at = timezone.now()
                updated_fields.extend(["last_verified_at", "updated_at"])

                if updated_fields:
                    channel_config.save(update_fields=list(set(updated_fields)))

                logger.info(
                    f"Updated chat config: profile_id={profile.id}, chat_id={chat_id}, " f"fields={updated_fields}"
                )

    def _handle_bot_removed(self, profile: Profile, chat_id: int, status: str):
        """Handle bot being removed from a channel/group."""

        try:
            channel_config = TelegramChatConfig.objects.get(profile=profile, chat_id=chat_id)

            channel_config.update_status(status)

            logger.info(f"Deactivated chat config: profile_id={profile.id}, chat_id={chat_id}, " f"status={status}")
        except TelegramChatConfig.DoesNotExist:
            logger.warning(f"Chat config not found for removal: profile_id={profile.id}, " f"chat_id={chat_id}")

    def _download_chat_photo(self, file_id: str) -> ContentFile | None:
        """Download chat photo from Telegram."""
        if not file_id:
            return None

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            return None

        try:
            # 1. Get file path
            response = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}", timeout=10)
            response.raise_for_status()
            file_path = response.json().get("result", {}).get("file_path")

            if not file_path:
                return None

            # 2. Download file
            file_response = requests.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}", timeout=10)
            file_response.raise_for_status()

            return ContentFile(file_response.content, name=f"tg_chat_{file_id}.jpg")
        except Exception as e:
            logger.error(f"Failed to download Telegram chat photo: {e}")
            return None

    def _verify_telegram_webhook(self, request) -> bool:
        """
        Verify webhook is from Telegram.

        Options:
        1. Check secret token in X-Telegram-Bot-Api-Secret-Token header
        2. IP whitelist (Telegram's webhook IPs)
        3. No verification (accept all - less secure but simpler)

        Current implementation: Secret token verification (recommended).
        """

        # Get secret token from settings (optional)
        webhook_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET_TOKEN", None)

        if not webhook_secret:
            # No secret configured - accept all webhooks
            logger.debug("TELEGRAM_WEBHOOK_SECRET_TOKEN not configured - accepting all webhooks")
            return True

        # Verify secret token from header
        received_token = request.META.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")

        if received_token != webhook_secret:
            logger.warning(f"Invalid webhook secret token from IP: {request.META.get('REMOTE_ADDR')}")
            return False

        return True
