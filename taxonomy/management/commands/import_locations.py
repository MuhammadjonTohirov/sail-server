from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from taxonomy.models import Location

from ._seed_utils import load_json_records, make_uz_slug, resolve_uzbekistan_data_dir


class Command(BaseCommand):
    help = "Import Uzbekistan regions and districts from the shared resources dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to the JSON directory or the shared resources root.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing location data before import.",
        )
        parser.add_argument(
            "--regions-only",
            action="store_true",
            help="Import only the 14 regions and skip districts/cities.",
        )

    def handle(self, *args, **options):
        data_dir = resolve_uzbekistan_data_dir(options.get("data_dir"))
        if not data_dir:
            raise CommandError("Uzbekistan JSON data directory not found. Pass --data-dir with a valid path.")

        if options["clear"]:
            self.stdout.write("Clearing existing location data...")
            Location.objects.all().delete()

        self.stdout.write(f"Using location dataset: {data_dir}")

        with transaction.atomic():
            country = self._upsert_country()
            regions = load_json_records(data_dir, "regions.json")
            region_map, region_created, region_updated = self._upsert_regions(country, regions)

            district_created = district_updated = 0
            city_created = city_updated = 0

            if not options["regions_only"]:
                districts = load_json_records(data_dir, "districts.json")
                district_created, district_updated, city_created, city_updated = self._upsert_districts(
                    region_map, districts
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Locations imported "
                f"(regions created: {region_created}, regions updated: {region_updated}, "
                f"districts created: {district_created}, districts updated: {district_updated}, "
                f"cities created: {city_created}, cities updated: {city_updated})."
            )
        )
        self.stdout.write(f"Total locations: {Location.objects.count()}")
        self.stdout.write(f"Regions: {Location.objects.filter(kind=Location.Kind.REGION).count()}")
        self.stdout.write(f"Districts: {Location.objects.filter(kind=Location.Kind.DISTRICT).count()}")
        self.stdout.write(f"Cities: {Location.objects.filter(kind=Location.Kind.CITY).count()}")

    def _upsert_country(self) -> Location:
        country, created = Location.objects.get_or_create(
            kind=Location.Kind.COUNTRY,
            slug="uzbekistan",
            defaults={
                "name": "Uzbekistan",
                "name_ru": "Узбекистан",
                "name_uz": "O'zbekiston",
            },
        )
        changed = False
        changed |= self._assign(country, "name", "Uzbekistan")
        changed |= self._assign(country, "name_ru", "Узбекистан")
        changed |= self._assign(country, "name_uz", "O'zbekiston")
        if changed and not created:
            country.save(update_fields=["name", "name_ru", "name_uz"])
        return country

    def _upsert_regions(self, country: Location, regions: list[dict]) -> tuple[dict[int, Location], int, int]:
        region_map: dict[int, Location] = {}
        created = 0
        updated = 0

        for row in regions:
            name_uz = self._clean_text(row.get("name_uz"))
            name_ru = self._clean_text(row.get("name_ru"))
            slug = make_uz_slug(name_uz)

            location = (
                Location.objects.filter(kind=Location.Kind.REGION, parent=country)
                .filter(Q(slug=slug) | Q(name_uz=name_uz) | Q(name_ru=name_ru) | Q(name=name_uz))
                .first()
            )

            was_created = location is None
            if location is None:
                location = Location(kind=Location.Kind.REGION, parent=country, slug=slug)

            changed = self._assign(location, "kind", Location.Kind.REGION)
            changed |= self._assign(location, "parent", country)
            changed |= self._assign(location, "name", name_uz)
            changed |= self._assign(location, "name_ru", name_ru)
            changed |= self._assign(location, "name_uz", name_uz)
            changed |= self._assign(location, "slug", slug)

            if was_created:
                location.save()
                created += 1
            elif changed:
                location.save(update_fields=["kind", "parent", "name", "name_ru", "name_uz", "slug"])
                updated += 1

            region_map[row["id"]] = location

        return region_map, created, updated

    def _upsert_districts(self, region_map: dict[int, Location], districts: list[dict]) -> tuple[int, int, int, int]:
        district_created = district_updated = 0
        city_created = city_updated = 0

        for row in districts:
            parent = region_map.get(row.get("region_id"))
            if not parent:
                self.stderr.write(f"Skipping district without parent region: {row.get('name_uz', '')}")
                continue

            name_uz = self._clean_text(row.get("name_uz"))
            name_ru = self._clean_text(row.get("name_ru"))
            slug = make_uz_slug(name_uz)
            kind = self._district_kind(row.get("soato_id"))

            location = (
                Location.objects.filter(parent=parent)
                .filter(Q(slug=slug) | Q(name_uz=name_uz) | Q(name_ru=name_ru) | Q(name=name_uz))
                .first()
            )

            was_created = location is None
            if location is None:
                location = Location(parent=parent, slug=slug, kind=kind)

            changed = self._assign(location, "kind", kind)
            changed |= self._assign(location, "parent", parent)
            changed |= self._assign(location, "name", name_uz)
            changed |= self._assign(location, "name_ru", name_ru)
            changed |= self._assign(location, "name_uz", name_uz)
            changed |= self._assign(location, "slug", slug)

            if was_created:
                location.save()
                if kind == Location.Kind.CITY:
                    city_created += 1
                else:
                    district_created += 1
            elif changed:
                location.save(update_fields=["kind", "parent", "name", "name_ru", "name_uz", "slug"])
                if kind == Location.Kind.CITY:
                    city_updated += 1
                else:
                    district_updated += 1

        return district_created, district_updated, city_created, city_updated

    def _district_kind(self, soato_id) -> str:
        soato = str(soato_id or "")
        return Location.Kind.CITY if soato[-3:].startswith("4") else Location.Kind.DISTRICT

    def _clean_text(self, value) -> str:
        return str(value or "").strip()

    def _assign(self, location: Location, field: str, value) -> bool:
        if getattr(location, field) == value:
            return False
        setattr(location, field, value)
        return True
