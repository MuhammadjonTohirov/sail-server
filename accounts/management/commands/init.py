from __future__ import annotations

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = (
        "Bootstrap a fresh install with foundational reference data: currencies, "
        "categories, category attributes, locations, and the OpenSearch index. "
        "Every step is idempotent, so the command is safe to re-run. No mock "
        "users or listings are created (use seed_mock_data for that)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--resources",
            type=str,
            default=None,
            help="Path to the shared resources directory for category icons.",
        )
        parser.add_argument(
            "--full-locations",
            action="store_true",
            help="Import the full region/district dataset from the shared resources "
                 "instead of the built-in regions and main cities.",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to the Uzbekistan JSON dataset. Implies --full-locations.",
        )
        parser.add_argument(
            "--regions-only",
            action="store_true",
            help="With --full-locations, import only the 14 regions and skip districts/cities.",
        )
        parser.add_argument(
            "--with-admin",
            action="store_true",
            help="Also create a superuser from env vars or defaults (dev only).",
        )
        parser.add_argument(
            "--refresh-icons",
            action="store_true",
            help="Re-upload category icons even when categories already exist.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing categories and locations before recreating them. Destructive.",
        )
        parser.add_argument(
            "--clear-attributes",
            action="store_true",
            help="Delete existing category attributes before recreating them.",
        )

    def handle(self, *args, **options):
        steps = self._build_steps(options)
        total = len(steps)
        for index, (title, command, kwargs) in enumerate(steps, start=1):
            self.stdout.write(self.style.NOTICE(f"{index}/{total} {title}"))
            call_command(command, **kwargs)
        self.stdout.write(self.style.SUCCESS("Initialization complete."))

    def _build_steps(self, options):
        clear = options["clear"]

        category_kwargs = {}
        if options.get("resources"):
            category_kwargs["resources"] = options["resources"]
        if clear:
            category_kwargs["clear"] = True
        if options["refresh_icons"]:
            category_kwargs["refresh_icons"] = True

        attribute_kwargs = {}
        if clear or options["clear_attributes"]:
            attribute_kwargs["clear"] = True

        steps = [
            ("Setting up currencies…", "setup_currencies", {}),
            ("Seeding categories…", "init_categories", category_kwargs),
            ("Seeding category attributes…", "init_category_attributes", attribute_kwargs),
            ("Seeding car attributes…", "init_car_attributes", {}),
            ("Importing locations…", *self._location_step(options, clear)),
            ("Ensuring search index…", "search_init_index", {}),
        ]
        if options["with_admin"]:
            steps.append(("Creating admin user…", "create_admin", {}))
        return steps

    def _location_step(self, options, clear):
        """Pick the lightweight built-in locations or the full dataset import."""
        full_locations = options["full_locations"] or bool(options.get("data_dir"))
        if not full_locations:
            return "init_locations", {}

        kwargs = {}
        if options.get("data_dir"):
            kwargs["data_dir"] = options["data_dir"]
        if clear:
            kwargs["clear"] = True
        if options["regions_only"]:
            kwargs["regions_only"] = True
        return "import_locations", kwargs
