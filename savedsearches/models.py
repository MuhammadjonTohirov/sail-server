from __future__ import annotations

from django.conf import settings
from django.db import models


class SavedSearch(models.Model):
    class Frequency(models.TextChoices):
        INSTANT = "instant", "Instant"
        DAILY = "daily", "Daily"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    title = models.CharField(max_length=255)
    query = models.JSONField(default=dict)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.DAILY)
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id}:{self.title}"

