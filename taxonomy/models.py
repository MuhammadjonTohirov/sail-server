from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class Location(models.Model):
    class Kind(models.TextChoices):
        COUNTRY = "COUNTRY", "Country"
        REGION = "REGION", "Region"
        CITY = "CITY", "City"
        DISTRICT = "DISTRICT", "District"

    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    name = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True, null=True)
    name_uz = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(max_length=255)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["parent"]),
        ]
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.kind})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    level = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, blank=True, default="")
    name_uz = models.CharField(max_length=255, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True)
    # Optional UI icon identifier (emoji or icon font key)
    icon = models.CharField(max_length=64, blank=True, default="")
    # Optional image icon for richer UI
    icon_image = models.ImageField(upload_to="category_icons/", null=True, blank=True)
    is_leaf = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["order"]),
        ]
        ordering = ["order", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.parent and self.level == 0:
            self.level = (self.parent.level or 0) + 1
        super().save(*args, **kwargs)


class Attribute(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        SELECT = "select", "Select"
        MULTISELECT = "multiselect", "Multiselect"
        RANGE = "range", "Range"

    category = models.ForeignKey(Category, related_name="attributes", on_delete=models.CASCADE)
    key = models.CharField(max_length=64)
    label = models.CharField(max_length=255)
    label_ru = models.CharField(max_length=255, blank=True, default="")
    label_uz = models.CharField(max_length=255, blank=True, default="")
    type = models.CharField(max_length=16, choices=Type.choices)
    unit = models.CharField(max_length=32, null=True, blank=True)
    options = models.JSONField(default=list, blank=True)
    is_indexed = models.BooleanField(default=True)
    # New: validation & UI hints
    is_required = models.BooleanField(default=False)
    min_number = models.FloatField(null=True, blank=True)
    max_number = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("category", "key")
        indexes = [
            models.Index(fields=["category", "key"]),
        ]
        ordering = ["key"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.category.name}:{self.key}"
