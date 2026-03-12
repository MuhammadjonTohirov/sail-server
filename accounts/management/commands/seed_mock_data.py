from __future__ import annotations

from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command
from django.db.models.signals import post_delete, post_save

from accounts.mock_seed import MOCK_EMAIL_DOMAIN
from listings.models import Listing
from listings.models import ListingAttributeValue, ListingMedia
from listings.signals import (
    on_attr_deleted,
    on_attr_saved,
    on_listing_deleted,
    on_listing_saved,
    on_media_deleted,
    on_media_saved,
)


class Command(BaseCommand):
    help = "Seed categories, Uzbekistan locations, mock users, and mock listings in one run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resources",
            type=str,
            default=None,
            help="Path to the shared resources directory for category icons.",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to the Uzbekistan JSON dataset or the shared resources root.",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=20,
            help="Number of mock users to create.",
        )
        parser.add_argument(
            "--listings",
            type=int,
            default=100,
            help="Number of mock listings to create.",
        )
        parser.add_argument(
            "--images-per-listing",
            type=int,
            default=1,
            help="Number of Picsum images to attach to each listing.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="mock_data/generated_users.json",
            help="Path for the exported generated user credentials JSON.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=20260312,
            help="Random seed used for listing generation.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seeded data before recreating it.",
        )
        parser.add_argument(
            "--refresh-icons",
            action="store_true",
            help="Re-upload category icons when categories already exist.",
        )
        parser.add_argument(
            "--clear-attributes",
            action="store_true",
            help="Delete existing category attributes before recreating them.",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Create listings without downloading Picsum images.",
        )
        parser.add_argument(
            "--regions-only",
            action="store_true",
            help="Import only the 14 regions and skip districts/cities.",
        )
        parser.add_argument(
            "--with-districts",
            action="store_true",
            help="Legacy flag kept for compatibility. Districts are now imported by default.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_dependent_mock_data()

        self.stdout.write(self.style.NOTICE("1/5 Seeding categories..."))
        category_kwargs = {}
        if options.get("resources"):
            category_kwargs["resources"] = options["resources"]
        if options["clear"]:
            category_kwargs["clear"] = True
        if options["refresh_icons"]:
            category_kwargs["refresh_icons"] = True
        call_command("init_categories", **category_kwargs)

        self.stdout.write(self.style.NOTICE("2/5 Seeding category attributes..."))
        attribute_kwargs = {}
        if options["clear"] or options["clear_attributes"]:
            attribute_kwargs["clear"] = True
        call_command("init_category_attributes", **attribute_kwargs)

        self.stdout.write(self.style.NOTICE("3/5 Importing locations..."))
        location_kwargs = {}
        if options.get("data_dir"):
            location_kwargs["data_dir"] = options["data_dir"]
        if options["clear"]:
            location_kwargs["clear"] = True
        if options["regions_only"]:
            location_kwargs["regions_only"] = True
        call_command("import_locations", **location_kwargs)

        self.stdout.write(self.style.NOTICE("4/5 Seeding mock users..."))
        user_kwargs = {
            "count": options["users"],
            "output": options["output"],
        }
        if options["clear"]:
            user_kwargs["clear"] = True
        call_command("seed_mock_users", **user_kwargs)

        self.stdout.write(self.style.NOTICE("5/5 Seeding mock listings..."))
        listing_kwargs = {
            "count": options["listings"],
            "images_per_listing": options["images_per_listing"],
            "seed": options["seed"],
        }
        if options["clear"]:
            listing_kwargs["clear"] = True
        if options["skip_images"]:
            listing_kwargs["skip_images"] = True
        call_command("seed_mock_listings", **listing_kwargs)

        self.stdout.write(self.style.SUCCESS("Mock data seed complete."))

    def _clear_dependent_mock_data(self):
        self.stdout.write(self.style.NOTICE("Pre-clearing existing mock listings and mock users..."))
        User = get_user_model()
        with self._mute_listing_index_signals():
            Listing.objects.filter(user__username__iendswith=f"@{MOCK_EMAIL_DOMAIN}").delete()
        User.objects.filter(username__iendswith=f"@{MOCK_EMAIL_DOMAIN}").delete()

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
