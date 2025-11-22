from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from taxonomy.models import Attribute, Category, Location


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending_review", "Pending Review"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"
        EXPIRED = "expired", "Expired"

    class Condition(models.TextChoices):
        NEW = "new", "New"
        USED = "used", "Used"

    class DealType(models.TextChoices):
        SELL = "sell", "Sell"
        EXCHANGE = "exchange", "Exchange"
        FREE = "free", "Free"

    class SellerType(models.TextChoices):
        PERSON = "person", "Person"
        BUSINESS = "business", "Business"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="listings")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    price_currency = models.CharField(max_length=3, default="UZS")
    condition = models.CharField(max_length=16, choices=Condition.choices, default=Condition.USED)
    deal_type = models.CharField(max_length=16, choices=DealType.choices, default=DealType.SELL)
    seller_type = models.CharField(max_length=16, choices=SellerType.choices, default=SellerType.PERSON)
    is_price_negotiable = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    refreshed_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    quality_score = models.FloatField(default=0.0)
    contact_phone_masked = models.CharField(max_length=32, blank=True, default="")
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    # Contact information
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(max_length=255, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["status", "category", "location", "refreshed_at"]),
        ]
        ordering = ["-refreshed_at", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class ListingAttributeValue(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="attributes")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    value_text = models.CharField(max_length=255, blank=True, default="")
    value_number = models.FloatField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_option_key = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["listing"]),
            models.Index(fields=["attribute"]),
        ]


def listing_media_upload_to(instance: "ListingMedia", filename: str) -> str:
    return f"listings/{instance.listing_id}/{filename}"


class ListingMedia(models.Model):
    class Type(models.TextChoices):
        PHOTO = "photo", "Photo"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media")
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.PHOTO)
    image = models.ImageField(upload_to=listing_media_upload_to)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
