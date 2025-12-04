from __future__ import annotations

from celery import shared_task

from .views.index import delete_listing, index_listing


@shared_task(name="search.index_listing")
def task_index_listing(listing_id: int):
    index_listing(listing_id)


@shared_task(name="search.delete_listing")
def task_delete_listing(listing_id: int):
    delete_listing(listing_id)

