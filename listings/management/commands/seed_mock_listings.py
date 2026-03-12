from __future__ import annotations

import random
from contextlib import contextmanager
from datetime import timedelta

import requests
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models.signals import post_delete, post_save
from django.utils import timezone

from accounts.mock_seed import MOCK_EMAIL_DOMAIN
from listings.mock_seed import build_listing_payload
from listings.models import Listing, ListingAttributeValue, ListingMedia
from listings.signals import (
    on_attr_deleted,
    on_attr_saved,
    on_listing_deleted,
    on_listing_saved,
    on_media_deleted,
    on_media_saved,
)
from taxonomy.models import Category, Location


class Command(BaseCommand):
    help = "Generate mock listings for the seeded mock users and attach Picsum images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="How many listings to generate.",
        )
        parser.add_argument(
            "--images-per-listing",
            type=int,
            default=1,
            help="How many Picsum images to attach to each listing.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing listings that belong to the generated mock users before inserting new ones.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=20260312,
            help="Random seed used for deterministic distribution.",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Create listings without downloading Picsum images.",
        )
        parser.add_argument(
            "--skip-search-reindex",
            action="store_true",
            help="Skip the final OpenSearch reindex step.",
        )

    def handle(self, *args, **options):
        count = options["count"]
        images_per_listing = max(options["images_per_listing"], 0)
        rng = random.Random(options["seed"])

        if count <= 0:
            raise CommandError("--count must be greater than 0.")

        User = get_user_model()
        users = list(User.objects.filter(username__iendswith=f"@{MOCK_EMAIL_DOMAIN}").order_by("id"))
        if not users:
            raise CommandError(
                "No generated mock users found. Run `python3 manage.py seed_mock_users` before seeding listings."
            )

        categories = list(Category.objects.filter(is_leaf=True).order_by("order", "id"))
        if not categories:
            raise CommandError(
                "No leaf categories found. Run `python3 manage.py init_categories` before seeding listings."
            )

        regions = list(Location.objects.filter(kind=Location.Kind.REGION).order_by("id"))
        if not regions:
            raise CommandError(
                "No regions found. Run `python3 manage.py import_locations` before seeding listings."
            )

        picsum_ids = []
        if not options["skip_images"] and images_per_listing > 0:
            picsum_ids = self._fetch_picsum_ids()
            if not picsum_ids:
                self.stdout.write(self.style.WARNING("Picsum ID discovery failed. Listings will be created without images."))

        if options["clear"]:
            self.stdout.write("Clearing existing mock-user listings...")
            with self._mute_listing_index_signals():
                Listing.objects.filter(user__in=users).delete()

        created = 0
        media_created = 0

        with self._mute_listing_index_signals():
            for sequence in range(1, count + 1):
                user = rng.choice(users)
                category = rng.choice(categories)
                region = rng.choice(regions)
                payload = build_listing_payload(category.slug, rng, sequence)
                profile = getattr(user, "profile", None)
                phone = getattr(profile, "phone_e164", "") or ""
                email = getattr(profile, "email", "") or user.email
                display_name = getattr(profile, "display_name", "") or user.get_full_name() or user.username

                listing = Listing.objects.create(
                    user=user,
                    category=category,
                    location=region,
                    title=payload["title"],
                    description=payload["description"],
                    price_amount=payload["price_amount"],
                    price_currency="UZS",
                    condition=payload["condition"],
                    deal_type=Listing.DealType.SELL,
                    seller_type=payload["seller_type"],
                    is_price_negotiable=payload["is_price_negotiable"],
                    status=Listing.Status.ACTIVE,
                    contact_phone_masked=self._mask_phone(phone),
                    contact_name=display_name,
                    contact_email=email,
                    contact_phone=phone,
                )

                created_at = timezone.now() - timedelta(
                    days=rng.randint(0, 45),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )
                Listing.objects.filter(pk=listing.pk).update(
                    created_at=created_at,
                    refreshed_at=created_at + timedelta(hours=rng.randint(0, 72)),
                    expires_at=created_at + timedelta(days=30),
                    quality_score=round(rng.uniform(0.7, 0.99), 2),
                    view_count=rng.randint(0, 500),
                    interest_count=rng.randint(0, 35),
                )

                if picsum_ids and images_per_listing > 0:
                    for order in range(images_per_listing):
                        media = self._create_listing_media(
                            listing=listing,
                            picsum_ids=picsum_ids,
                            seed_value=sequence * 10 + order,
                        )
                        media_created += int(media is not None)

                created += 1
                if sequence % 10 == 0:
                    self.stdout.write(f"Created {sequence}/{count} listings...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock listings seeded (created: {created}, media created: {media_created})."
            )
        )

        if not options["skip_search_reindex"]:
            self.stdout.write("Reindexing search documents...")
            try:
                call_command("search_reindex", clear=True, delete_stale=True)
            except Exception as exc:
                self.stderr.write(f"Search reindex failed after seeding listings: {exc}")

    def _fetch_picsum_ids(self) -> list[int]:
        fallback = [10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35, 237]
        try:
            response = requests.get("https://picsum.photos/v2/list?page=1&limit=100", timeout=20)
            response.raise_for_status()
            data = response.json()
            ids = [int(row["id"]) for row in data if str(row.get("id", "")).isdigit()]
            return ids or fallback
        except requests.RequestException:
            return fallback

    def _create_listing_media(self, *, listing: Listing, picsum_ids: list[int], seed_value: int) -> ListingMedia | None:
        if not picsum_ids:
            return None

        for offset in range(min(len(picsum_ids), 8)):
            image_id = picsum_ids[(seed_value + offset) % len(picsum_ids)]
            image_url = f"https://picsum.photos/id/{image_id}/500/500"

            try:
                response = requests.get(image_url, timeout=20)
                response.raise_for_status()
            except requests.RequestException:
                continue

            content = ContentFile(response.content, name=f"listing_{listing.id}_{image_id}.jpg")
            return ListingMedia.objects.create(
                listing=listing,
                image=content,
                type=ListingMedia.Type.PHOTO,
                width=500,
                height=500,
                order=listing.media.count(),
            )

        self.stderr.write(f"Failed to download Picsum image for listing {listing.id}")
        return None

    def _mask_phone(self, phone: str) -> str:
        if len(phone) < 5:
            return phone
        return f"{phone[:4]}****{phone[-2:]}"

    @contextmanager
    def _mute_listing_index_signals(self):
        connections = [
            (post_save, on_listing_saved, Listing),
            (post_delete, on_listing_deleted, Listing),
            (post_save, on_attr_saved, ListingAttributeValue),
            (post_delete, on_attr_deleted, ListingAttributeValue),
            (post_save, on_media_saved, ListingMedia),
            (post_delete, on_media_deleted, ListingMedia),
        ]

        for signal, receiver, sender in connections:
            signal.disconnect(receiver, sender=sender)

        try:
            yield
        finally:
            for signal, receiver, sender in connections:
                signal.connect(receiver, sender=sender)
