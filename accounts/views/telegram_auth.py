"""Telegram-based authentication views."""
from __future__ import annotations

import hashlib
import hmac
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Profile
from ..serializers import ProfileSerializer, TelegramLoginSerializer
from .base import download_telegram_photo


logger = logging.getLogger(__name__)
User = get_user_model()


class TelegramLoginView(APIView):
    """Authenticate users via Telegram Login widget."""
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "auth"

    def post(self, request):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.warning("Telegram login attempted but TELEGRAM_BOT_TOKEN not configured")
            return Response({"detail": "Telegram login not configured."}, status=503)

        serializer = TelegramLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.warning(f"Invalid Telegram login data: {e}")
            return Response({"detail": "Invalid Telegram login data."}, status=400)

        data = serializer.validated_data
        telegram_id = data["id"]

        # Verify signature
        if not self._verify_hash(data, bot_token):
            logger.warning(
                f"Invalid Telegram login signature for telegram_id={telegram_id}, "
                f"ip={request.META.get('REMOTE_ADDR')}"
            )
            return Response({"detail": "Invalid Telegram login signature."}, status=400)

        # Verify timestamp
        max_age = getattr(settings, "TELEGRAM_LOGIN_MAX_AGE", 86400)
        now_ts = int(timezone.now().timestamp())
        auth_date = data["auth_date"]
        if now_ts - auth_date > max_age:
            logger.warning(
                f"Expired Telegram login for telegram_id={telegram_id}, "
                f"auth_date={auth_date}, age={now_ts - auth_date}s"
            )
            return Response({"detail": "Telegram login request expired."}, status=400)

        username = data.get("username") or ""
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        photo_url = data.get("photo_url", "")
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()

        try:
            with transaction.atomic():
                # Check for existing profile
                profile = Profile.objects.filter(telegram_id=telegram_id).select_related("user").first()

                if profile:
                    # Existing user - update fields only if changed
                    user = profile.user
                    logger.info(f"Existing Telegram user login: telegram_id={telegram_id}, user_id={user.id}")

                    # Update User fields if needed
                    user_updates: list[str] = []
                    if first_name and user.first_name != first_name[:150]:
                        user.first_name = first_name[:150]
                        user_updates.append("first_name")
                    if last_name and user.last_name != last_name[:150]:
                        user.last_name = last_name[:150]
                        user_updates.append("last_name")
                    if user_updates:
                        user.save(update_fields=user_updates)

                    # Update Profile fields if needed
                    updated_fields: list[str] = []

                    if username and profile.telegram_username != username:
                        profile.telegram_username = username
                        updated_fields.append("telegram_username")

                    if photo_url and profile.telegram_photo_url != photo_url:
                        profile.telegram_photo_url = photo_url
                        updated_fields.append("telegram_photo_url")

                        # Download and update logo if photo URL changed
                        photo_file = download_telegram_photo(photo_url, telegram_id)
                        if photo_file:
                            # Delete old logo if exists
                            if profile.logo:
                                try:
                                    profile.logo.delete(save=False)
                                except Exception as e:
                                    logger.warning(f"Failed to delete old Telegram photo: {e}")

                            profile.logo = photo_file
                            updated_fields.append("logo")
                            logger.info(f"Downloaded Telegram photo for user_id={user.id}")

                    desired_name = full_name or username or profile.display_name or f"tg_{telegram_id}"
                    if profile.display_name != desired_name:
                        profile.display_name = desired_name
                        updated_fields.append("display_name")

                    if updated_fields:
                        profile.save(update_fields=list(set(updated_fields)))

                else:
                    # New user - create User and Profile
                    user_username = f"tg_{telegram_id}"
                    user_defaults = {
                        "first_name": first_name[:150],
                        "last_name": last_name[:150],
                    }
                    user, created = User.objects.get_or_create(username=user_username, defaults=user_defaults)

                    if created:
                        user.set_unusable_password()

                    # Download Telegram photo
                    photo_file = download_telegram_photo(photo_url, telegram_id) if photo_url else None

                    profile_defaults = {
                        "phone_e164": f"tg:{telegram_id}",
                        "display_name": full_name or username or user_username,
                        "telegram_id": telegram_id,
                        "telegram_username": username,
                        "telegram_photo_url": photo_url or "",
                    }

                    if photo_file:
                        profile_defaults["logo"] = photo_file

                    profile, _ = Profile.objects.get_or_create(user=user, defaults=profile_defaults)

                    logger.info(
                        f"New Telegram user created: telegram_id={telegram_id}, "
                        f"user_id={user.id}, username={username}"
                    )

            # Generate tokens
            refresh = RefreshToken.for_user(profile.user)
            logger.info(f"Telegram login successful: telegram_id={telegram_id}, user_id={profile.user.id}")

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "profile": ProfileSerializer(profile).data,
                },
                status=200,
            )

        except Exception as e:
            logger.error(f"Telegram login failed for telegram_id={telegram_id}: {e}", exc_info=True)
            return Response(
                {"detail": "An error occurred during Telegram login. Please try again."},
                status=500
            )

    @staticmethod
    def _verify_hash(data: dict, bot_token: str) -> bool:
        """Verify Telegram login widget signature."""
        received_hash = data.get("hash", "")
        payload_items = []
        for key in sorted(k for k in data.keys() if k != "hash"):
            value = data[key]
            if value is None:
                value = ""
            payload_items.append(f"{key}={value}")
        data_check_string = "\n".join(payload_items)
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed_hash, received_hash)
