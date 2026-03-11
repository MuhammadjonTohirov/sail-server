"""Security-related views (password change, account linking)."""
from __future__ import annotations

import hashlib
import hmac
import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile
from ..serializers import ProfileSerializer
from .base import download_telegram_photo


logger = logging.getLogger(__name__)


class ChangePasswordView(APIView):
    """Change password for authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["security"],
        summary="Change password",
        description="Change the password for the authenticated user. Requires the current password for verification.",
        responses={200: None, 400: None},
        examples=[
            OpenApiExample(
                "Request body",
                value={"current_password": "oldpass123", "new_password": "newpass456"},
                request_only=True,
            ),
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"status": "password_changed"}, "error": None, "code": 200},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Wrong current password",
                value={"success": False, "data": None, "error": "Current password is incorrect.", "code": 400},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"detail": "Both current_password and new_password are required."}, status=400)

        if len(new_password) < 8:
            return Response({"detail": "New password must be at least 8 characters."}, status=400)

        user = request.user

        # Check if user has a usable password (not Telegram-only user)
        if not user.has_usable_password():
            return Response({"detail": "Cannot change password. Account was created via Telegram."}, status=400)

        # Verify current password
        if not user.check_password(current_password):
            return Response({"detail": "Current password is incorrect."}, status=400)

        # Set new password
        user.set_password(new_password)
        user.save()

        return Response({"status": "password_changed"}, status=200)


class SetPasswordView(APIView):
    """Set password for user who doesn't have one (e.g., Telegram-only user)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["security"],
        summary="Set password",
        description="Set a password for users who do not have one (e.g., Telegram-only accounts). "
        "Users who already have a password should use the change-password endpoint instead.",
        responses={200: None, 400: None},
        examples=[
            OpenApiExample(
                "Request body",
                value={"new_password": "securepass123"},
                request_only=True,
            ),
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"status": "password_set"}, "error": None, "code": 200},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Already has password",
                value={
                    "success": False,
                    "data": None,
                    "error": "User already has a password. Use change-password endpoint.",
                    "code": 400,
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        new_password = request.data.get("new_password")

        if not new_password:
            return Response({"detail": "new_password is required."}, status=400)

        if len(new_password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)

        user = request.user

        # Only allow if user doesn't have a usable password
        if user.has_usable_password():
            return Response({"detail": "User already has a password. Use change-password endpoint."}, status=400)

        # Set password
        user.set_password(new_password)
        user.save()

        return Response({"status": "password_set"}, status=200)


class LinkTelegramView(APIView):
    """Link Telegram account to existing user account."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["security"],
        summary="Link Telegram account",
        description="Link a Telegram account to the authenticated user using Telegram Login Widget data. "
        "Verifies the signature and prevents linking to an already-linked Telegram account.",
        responses={200: None, 400: None, 404: None, 503: None},
        examples=[
            OpenApiExample(
                "Request body",
                value={
                    "id": 123456789,
                    "first_name": "John",
                    "username": "johndoe",
                    "photo_url": "https://t.me/i/userpic/...",
                    "auth_date": 1700000000,
                    "hash": "abc123...",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "status": "telegram_linked",
                        "profile": {"user_id": 1, "telegram_id": 123456789, "telegram_username": "johndoe"},
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Already linked",
                value={
                    "success": False,
                    "data": None,
                    "error": "This Telegram account is already linked to another user.",
                    "code": 400,
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.warning("Telegram link attempted but TELEGRAM_BOT_TOKEN not configured")
            return Response({"detail": "Telegram integration not configured."}, status=503)

        # Extract Telegram data
        telegram_id = request.data.get("id")
        auth_date = request.data.get("auth_date")
        hash_value = request.data.get("hash")

        if not all([telegram_id, auth_date, hash_value]):
            return Response({"detail": "Invalid Telegram data."}, status=400)

        # Verify signature
        if not self._verify_hash(request.data, bot_token):
            logger.warning(
                f"Invalid Telegram link signature for telegram_id={telegram_id}, "
                f"user_id={request.user.id}, ip={request.META.get('REMOTE_ADDR')}"
            )
            return Response({"detail": "Invalid Telegram signature."}, status=400)

        # Verify timestamp (max 1 day old)
        max_age = getattr(settings, "TELEGRAM_LOGIN_MAX_AGE", 86400)
        now_ts = int(timezone.now().timestamp())
        if now_ts - int(auth_date) > max_age:
            return Response({"detail": "Telegram authentication expired."}, status=400)

        # Check if this Telegram ID is already linked to another account
        existing_profile = Profile.objects.filter(telegram_id=telegram_id).exclude(user=request.user).first()
        if existing_profile:
            return Response({"detail": "This Telegram account is already linked to another user."}, status=400)

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=404)

        # Extract Telegram user data
        username = request.data.get("username") or ""
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        photo_url = request.data.get("photo_url", "")
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()

        with transaction.atomic():
            # Update profile with Telegram data
            profile.telegram_id = telegram_id
            profile.telegram_username = username
            profile.telegram_photo_url = photo_url

            # Download Telegram photo if available and user doesn't have a logo
            if photo_url and not profile.logo:
                photo_file = download_telegram_photo(photo_url, telegram_id)
                if photo_file:
                    profile.logo = photo_file

            # Update display name if empty
            if not profile.display_name and full_name:
                profile.display_name = full_name

            profile.save()

            logger.info(f"Telegram account linked: user_id={request.user.id}, telegram_id={telegram_id}")

        return Response({
            "status": "telegram_linked",
            "profile": ProfileSerializer(profile).data,
        }, status=200)

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


class UnlinkTelegramView(APIView):
    """Unlink Telegram account from user account."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["security"],
        summary="Unlink Telegram account",
        description="Remove the linked Telegram account from the authenticated user. "
        "Requires the user to have an alternative login method (email/phone with password).",
        responses={200: None, 400: None, 404: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "status": "telegram_unlinked",
                        "profile": {"user_id": 1, "telegram_id": None, "telegram_username": ""},
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "No Telegram linked",
                value={"success": False, "data": None, "error": "No Telegram account linked.", "code": 400},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Cannot unlink",
                value={
                    "success": False,
                    "data": None,
                    "error": "Cannot unlink Telegram. You need an email/phone with password to login.",
                    "code": 400,
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=404)

        if not profile.telegram_id:
            return Response({"detail": "No Telegram account linked."}, status=400)

        # Check if user has other login methods (email/phone + password)
        user = request.user
        has_password = user.has_usable_password()
        has_email = bool(profile.email)
        has_phone = bool(profile.phone_e164)

        if not has_password or (not has_email and not has_phone):
            return Response({
                "detail": "Cannot unlink Telegram. You need an email/phone with password to login."
            }, status=400)

        # Clear Telegram data
        profile.telegram_id = None
        profile.telegram_username = ""
        profile.telegram_photo_url = ""
        profile.save(update_fields=["telegram_id", "telegram_username", "telegram_photo_url"])

        logger.info(f"Telegram account unlinked: user_id={request.user.id}")

        return Response({
            "status": "telegram_unlinked",
            "profile": ProfileSerializer(profile).data,
        }, status=200)


class AccountSecurityInfoView(APIView):
    """Get security info about the user's account."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["security"],
        summary="Get account security info",
        description="Return information about the authenticated user's security settings, "
        "including which login methods are configured.",
        responses={200: None, 404: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "has_password": True,
                        "has_email": True,
                        "has_phone": True,
                        "has_telegram": False,
                        "telegram_username": None,
                        "email": "user@example.com",
                        "phone": "+998901234567",
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Profile not found",
                value={"success": False, "data": None, "error": "Profile not found.", "code": 404},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=404)

        return Response({
            "has_password": user.has_usable_password(),
            "has_email": bool(profile.email),
            "has_phone": bool(profile.phone_e164),
            "has_telegram": bool(profile.telegram_id),
            "telegram_username": profile.telegram_username or None,
            "email": profile.email or None,
            "phone": profile.phone_e164 or None,
        }, status=200)
