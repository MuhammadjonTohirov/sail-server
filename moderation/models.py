from __future__ import annotations

from django.conf import settings
from django.db import models

from listings.models import Listing


class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason_code = models.CharField(max_length=64)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Report {self.id} on {self.listing_id}"

