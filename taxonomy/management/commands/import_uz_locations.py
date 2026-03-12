from __future__ import annotations

from .import_locations import Command as ImportLocationsCommand


class Command(ImportLocationsCommand):
    help = "Backward-compatible alias for importing Uzbekistan locations with the current schema."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--districts-only",
            action="store_true",
            help="Legacy flag retained for compatibility. Villages and quarters are no longer supported by the current model.",
        )

    def handle(self, *args, **options):
        if not options.get("districts_only"):
            self.stdout.write(
                self.style.WARNING(
                    "The current Location model supports COUNTRY, REGION, CITY, and DISTRICT only. "
                    "Villages and quarters will be skipped."
                )
            )
        return super().handle(*args, **options)
