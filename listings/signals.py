from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from searchapp.tasks import task_delete_listing, task_index_listing

from .models import Listing, ListingAttributeValue, ListingMedia


@receiver(post_save, sender=Listing)
def on_listing_saved(sender, instance: Listing, created, **kwargs):
    task_index_listing.delay(instance.id)


@receiver(post_delete, sender=Listing)
def on_listing_deleted(sender, instance: Listing, **kwargs):
    task_delete_listing.delay(instance.id)


@receiver(post_save, sender=ListingAttributeValue)
def on_attr_saved(sender, instance: ListingAttributeValue, created, **kwargs):
    task_index_listing.delay(instance.listing_id)


@receiver(post_delete, sender=ListingAttributeValue)
def on_attr_deleted(sender, instance: ListingAttributeValue, **kwargs):
    task_index_listing.delay(instance.listing_id)


@receiver(post_save, sender=ListingMedia)
def on_media_saved(sender, instance: ListingMedia, created, **kwargs):
    task_index_listing.delay(instance.listing_id)


@receiver(post_delete, sender=ListingMedia)
def on_media_deleted(sender, instance: ListingMedia, **kwargs):
    task_index_listing.delay(instance.listing_id)

