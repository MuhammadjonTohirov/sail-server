from __future__ import annotations

from django.conf import settings
from django.db import models


class FavoriteListing(models.Model):
    """
    User's favorite/liked listings.
    Allows users to save listings they're interested in for later viewing.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_listings"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user", "listing"]]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["listing"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.listing_id}"


class RecentlyViewedListing(models.Model):
    """
    Track recently viewed listings for each user.
    Used to show "Recently Viewed" section and for recommendations.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recently_viewed_listings",
        null=True,
        blank=True
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="viewed_by"
    )
    # For anonymous users, track by session
    session_key = models.CharField(max_length=40, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now=True)  # Updates on each view
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["session_key", "-viewed_at"]),
            models.Index(fields=["listing"]),
        ]
        ordering = ["-viewed_at"]
        # Allow one record per user+listing or session+listing
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"],
                condition=models.Q(user__isnull=False),
                name="unique_user_listing"
            ),
            models.UniqueConstraint(
                fields=["session_key", "listing"],
                condition=models.Q(session_key__isnull=False),
                name="unique_session_listing"
            ),
        ]

    def __str__(self) -> str:
        if self.user:
            return f"{self.user_id} viewed {self.listing_id}"
        return f"Session {self.session_key} viewed {self.listing_id}"
