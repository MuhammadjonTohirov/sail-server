from __future__ import annotations

import logging
from typing import Callable

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from searchapp.tasks import task_delete_listing, task_index_listing
from searchapp.views.index import delete_listing, index_listing

from .models import Listing, ListingAttributeValue, ListingMedia

logger = logging.getLogger(__name__)


def _dispatch_search_task(task, fallback: Callable[[int], None], listing_id: int) -> None:
    def runner() -> None:
        try:
            task.delay(listing_id)
        except Exception:
            logger.warning(
                "Search task dispatch failed for listing %s; falling back to inline sync.",
                listing_id,
                exc_info=True,
            )
            try:
                fallback(listing_id)
            except Exception:
                logger.exception("Inline search sync failed for listing %s.", listing_id)

    transaction.on_commit(runner)


@receiver(post_save, sender=Listing)
def on_listing_saved(sender, instance: Listing, created, **kwargs):
    _dispatch_search_task(task_index_listing, index_listing, instance.id)


@receiver(post_delete, sender=Listing)
def on_listing_deleted(sender, instance: Listing, **kwargs):
    _dispatch_search_task(task_delete_listing, delete_listing, instance.id)


@receiver(post_save, sender=ListingAttributeValue)
def on_attr_saved(sender, instance: ListingAttributeValue, created, **kwargs):
    _dispatch_search_task(task_index_listing, index_listing, instance.listing_id)


@receiver(post_delete, sender=ListingAttributeValue)
def on_attr_deleted(sender, instance: ListingAttributeValue, **kwargs):
    _dispatch_search_task(task_index_listing, index_listing, instance.listing_id)


@receiver(post_save, sender=ListingMedia)
def on_media_saved(sender, instance: ListingMedia, created, **kwargs):
    _dispatch_search_task(task_index_listing, index_listing, instance.listing_id)


@receiver(post_delete, sender=ListingMedia)
def on_media_deleted(sender, instance: ListingMedia, **kwargs):
    _dispatch_search_task(task_index_listing, index_listing, instance.listing_id)
