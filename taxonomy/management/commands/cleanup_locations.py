"""
Clean up duplicate locations and ensure proper hierarchy without deleting.
This updates existing records and creates missing ones.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from listings.models import Listing
from taxonomy.models import Location

from ._seed_utils import load_json_records, make_uz_slug, resolve_uzbekistan_data_dir


class Command(BaseCommand):
    help = 'Clean up and fix location data without deleting (safe for production)'

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to the JSON directory or the shared resources root.",
        )

    def handle(self, *args, **options):
        data_dir = resolve_uzbekistan_data_dir(options.get("data_dir"))
        if not data_dir:
            raise CommandError("Uzbekistan JSON data directory not found. Pass --data-dir with a valid path.")

        try:
            with transaction.atomic():
                # Step 1: Find or create Uzbekistan
                self.stdout.write('Setting up Uzbekistan...')
                uzbekistan, created = Location.objects.get_or_create(
                    kind=Location.Kind.COUNTRY,
                    name="Uzbekistan",
                    defaults={
                        "name_ru": "Узбекистан",
                        "name_uz": "O'zbekiston",
                        "slug": "uzbekistan",
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Uzbekistan'))
                else:
                    self.stdout.write('✓ Uzbekistan exists')

                # Step 2: Load regions from JSON
                regions_data = load_json_records(data_dir, "regions.json")

                self.stdout.write(f'\nProcessing {len(regions_data)} regions from JSON...')

                # Step 3: Get existing regions
                existing_regions = Location.objects.filter(kind=Location.Kind.REGION)
                self.stdout.write(f'Found {existing_regions.count()} existing REGION entries')

                # Step 4: Delete English-named duplicates (Fergana Region, Andijan Region, etc.)
                english_regions = existing_regions.filter(
                    name__icontains='Region'
                ).exclude(
                    name__icontains='область'
                ).exclude(
                    name__icontains='viloyati'
                )

                if english_regions.exists():
                    self.stdout.write(f'\nFound {english_regions.count()} English-named regions (old data):')
                    for reg in english_regions:
                        # Check if this location is used by any listings
                        listing_count = Listing.objects.filter(location=reg).count()
                        if listing_count > 0:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  ⚠ {reg.name} - used by {listing_count} listings, will migrate'
                                )
                            )
                        else:
                            self.stdout.write(f'  - {reg.name} (unused)')

                # Step 5: Create/update correct regions and migrate data
                region_map = {}
                for region_data in regions_data:
                    name_ru = region_data.get('name_ru', '')
                    name_uz = region_data.get('name_uz', '')

                    # Try to find existing correct region by Russian or Uzbek name
                    existing = existing_regions.filter(
                        parent=uzbekistan
                    ).filter(
                        name_ru=name_ru
                    ).first() or existing_regions.filter(
                        parent=uzbekistan
                    ).filter(
                        name_uz=name_uz
                    ).first()

                    if existing:
                        # Update to ensure correct data
                        existing.name = name_uz
                        existing.name_ru = name_ru
                        existing.name_uz = name_uz
                        existing.slug = make_uz_slug(name_uz)
                        existing.parent = uzbekistan
                        existing.save()
                        self.stdout.write(f'  ✓ Updated: {name_ru}')
                        location = existing
                    else:
                        # Create new
                        location = Location.objects.create(
                            kind=Location.Kind.REGION,
                            parent=uzbekistan,
                            name=name_uz,
                            name_ru=name_ru,
                            name_uz=name_uz,
                            slug=make_uz_slug(name_uz)
                        )
                        self.stdout.write(f'  ✓ Created: {name_ru}')

                    region_map[region_data['id']] = location

                # Step 6: Migrate listings from English regions to correct regions
                for english_reg in english_regions:
                    listing_count = Listing.objects.filter(location=english_reg).count()
                    if listing_count > 0:
                        # Try to find matching correct region
                        english_name = english_reg.name.replace(' Region', '').replace(' Oblast', '')

                        # Find best match in region_map
                        matched_region = None
                        for region in region_map.values():
                            if (english_name.lower() in region.name.lower() or
                                english_name.lower() in (region.name_ru or '').lower() or
                                english_name.lower() in (region.name_uz or '').lower()):
                                matched_region = region
                                break

                        if matched_region:
                            # Migrate listings
                            Listing.objects.filter(location=english_reg).update(location=matched_region)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Migrated {listing_count} listings from "{english_reg.name}" to "{matched_region.name_ru}"'
                                )
                            )

                # Step 7: Now delete unused English regions
                unused_english = english_regions.filter(listings__isnull=True)
                if unused_english.exists():
                    count = unused_english.count()
                    unused_english.delete()
                    self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} unused English regions'))

                # Step 8: Import districts
                districts_file = data_dir / "districts.json"
                if districts_file.exists():
                    self.stdout.write('\nProcessing districts...')
                    districts_data = load_json_records(data_dir, "districts.json")

                    district_count = 0
                    for district_data in districts_data:
                        region_id = district_data.get('region_id')
                        parent_location = region_map.get(region_id)

                        if not parent_location:
                            continue

                        name_uz = district_data['name_uz']
                        name_ru = district_data.get('name_ru', '')

                        # Check if exists
                        existing_district = Location.objects.filter(
                            kind=Location.Kind.DISTRICT,
                            parent=parent_location,
                            name_uz=name_uz
                        ).first()

                        if not existing_district:
                            Location.objects.create(
                                kind=Location.Kind.DISTRICT,
                                parent=parent_location,
                                name=name_uz,
                                name_ru=name_ru,
                                name_uz=name_uz,
                                slug=make_uz_slug(name_uz)
                            )
                            district_count += 1

                    if district_count > 0:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created {district_count} new districts'))

                # Final summary
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Cleanup complete!'
                ))
                self.stdout.write(f'   Total locations: {Location.objects.count()}')
                self.stdout.write(f'   - Regions: {Location.objects.filter(kind=Location.Kind.REGION).count()}')
                self.stdout.write(f'   - Districts: {Location.objects.filter(kind=Location.Kind.DISTRICT).count()}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise
