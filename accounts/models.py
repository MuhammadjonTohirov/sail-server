from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


def profile_logo_upload_to(instance: "Profile", filename: str) -> str:
    return f"profiles/{instance.user_id}/logo/{filename}"


def profile_banner_upload_to(instance: "Profile", filename: str) -> str:
    return f"profiles/{instance.user_id}/banner/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone_e164 = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=255, blank=True, default="", db_index=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    about = models.TextField(blank=True, default="")

    # Settings page fields
    location = models.ForeignKey('taxonomy.Location', on_delete=models.SET_NULL, null=True, blank=True, related_name="user_profiles")
    logo = models.ImageField(upload_to=profile_logo_upload_to, null=True, blank=True)
    banner = models.ImageField(upload_to=profile_banner_upload_to, null=True, blank=True)

    # Telegram integration (optional)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    telegram_photo_url = models.URLField(blank=True, default="")

    last_active_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.display_name or self.phone_e164}"


class OtpCode(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        PASSWORD_RESET = "password_reset", "Password Reset"

    phone_e164 = models.CharField(max_length=20)
    email = models.EmailField(max_length=255, blank=True, default="")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.LOGIN)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    ip_addr = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone_e164", "expires_at"]),
            models.Index(fields=["email", "expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    @classmethod
    def create_new(cls, phone: str = "", email: str = "", code: str = "", purpose: str = Purpose.LOGIN, minutes_valid: int = 5, ip: str | None = None) -> "OtpCode":
        return cls.objects.create(
            phone_e164=phone,
            email=email,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=minutes_valid),
            ip_addr=ip,
        )


class TelegramChatConfig(models.Model):
    """
    Stores Telegram channel/group configurations for users.
    Automatically populated when user adds bot as administrator to their chat.
    """

    # Relationships
    profile = models.ForeignKey(
        "Profile",
        on_delete=models.CASCADE,
        related_name="telegram_chats",
        help_text="User profile that owns this chat configuration",
    )

    # Chat identification
    chat_id = models.BigIntegerField(
        db_index=True,
        help_text="Telegram channel/group chat ID",
    )

    # Chat metadata (snapshot at connection time)
    chat_type = models.CharField(
        max_length=20,
        help_text="Type: channel, supergroup, group",
    )
    chat_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Channel/group title",
    )
    chat_username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Channel/group username (if public)",
    )
    chat_photo = models.ImageField(
        upload_to="telegram_chats/",
        null=True,
        blank=True,
        help_text="Chat photo/avatar",
    )

    # Bot status in chat
    is_active = models.BooleanField(
        default=True,
        help_text="Whether bot is currently active in chat",
    )
    bot_status = models.CharField(
        max_length=20,
        default="administrator",
        help_text="Bot's current status: administrator, member, left, kicked",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time bot status was verified",
    )

    class Meta:
        db_table = "telegram_chat_configs"
        unique_together = [["profile", "chat_id"]]  # Prevent duplicate chat connections
        indexes = [
            models.Index(fields=["chat_id", "is_active"]),
            models.Index(fields=["profile", "is_active"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.chat_title or self.chat_id} ({self.profile.display_name})"

    def deactivate(self):
        """Mark chat as inactive (bot removed or kicked)."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def reactivate(self):
        """Mark chat as active (bot re-added)."""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    def update_status(self, new_status: str):
        """Update bot status in chat."""
        self.bot_status = new_status
        self.last_verified_at = timezone.now()

        # Auto-update is_active based on status
        if new_status in ["left", "kicked"]:
            self.is_active = False
        elif new_status in ["administrator", "member"]:
            self.is_active = True

        self.save(update_fields=["bot_status", "is_active", "last_verified_at", "updated_at"])
