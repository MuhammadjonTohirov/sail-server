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
    phone_e164 = models.CharField(max_length=20, unique=True)
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
