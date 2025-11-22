"""
Clean up duplicate locations and ensure proper hierarchy without deleting.
This updates existing records and creates missing ones.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from taxonomy.models import Location
from listings.models import Listing


class Command(BaseCommand):
    help = 'Clean up and fix location data without deleting (safe for production)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='resources/uzbekistan-regions-data-master/JSON',
            help='Path to the directory containing JSON files'
        )

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])

        if not data_dir.exists():
            self.stdout.write(self.style.ERROR(f'Data directory not found: {data_dir}'))
            return

        try:
            with transaction.atomic():
                # Step 1: Find or create Uzbekistan
                self.stdout.write('Setting up Uzbekistan...')
                uzbekistan, created = Location.objects.get_or_create(
                    kind='COUNTRY',
                    name='Uzbekistan',
                    defaults={
                        'name_ru': 'Узбекистан',
                        'name_uz': 'O\'zbekiston',
                        'slug': 'uzbekistan',
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Uzbekistan'))
                else:
                    self.stdout.write('✓ Uzbekistan exists')

                # Step 2: Load regions from JSON
                regions_file = data_dir / 'regions.json'
                if not regions_file.exists():
                    self.stdout.write(self.style.ERROR('regions.json not found'))
                    return

                with open(regions_file, 'r', encoding='utf-8-sig') as f:
                    regions_data = json.load(f)

                self.stdout.write(f'\nProcessing {len(regions_data)} regions from JSON...')

                # Step 3: Get existing regions
                existing_regions = Location.objects.filter(kind='REGION')
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
                        existing.slug = self._make_slug(name_uz)
                        existing.parent = uzbekistan
                        existing.save()
                        self.stdout.write(f'  ✓ Updated: {name_ru}')
                        location = existing
                    else:
                        # Create new
                        location = Location.objects.create(
                            kind='REGION',
                            parent=uzbekistan,
                            name=name_uz,
                            name_ru=name_ru,
                            name_uz=name_uz,
                            slug=self._make_slug(name_uz)
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
                districts_file = data_dir / 'districts.json'
                if districts_file.exists():
                    self.stdout.write('\nProcessing districts...')
                    with open(districts_file, 'r', encoding='utf-8-sig') as f:
                        districts_data = json.load(f)

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
                            kind='DISTRICT',
                            parent=parent_location,
                            name_uz=name_uz
                        ).first()

                        if not existing_district:
                            Location.objects.create(
                                kind='DISTRICT',
                                parent=parent_location,
                                name=name_uz,
                                name_ru=name_ru,
                                name_uz=name_uz,
                                slug=self._make_slug(name_uz)
                            )
                            district_count += 1

                    if district_count > 0:
                        self.stdout.write(self.style.SUCCESS(f'✓ Created {district_count} new districts'))

                # Final summary
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Cleanup complete!'
                ))
                self.stdout.write(f'   Total locations: {Location.objects.count()}')
                self.stdout.write(f'   - Regions: {Location.objects.filter(kind="REGION").count()}')
                self.stdout.write(f'   - Districts: {Location.objects.filter(kind="DISTRICT").count()}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise

    def _make_slug(self, name):
        """Create URL-safe slug from Uzbek/Russian text"""
        replacements = {
            'ʻ': '', "'": '', '\'': '',
            'ў': 'o', 'ғ': 'g', 'қ': 'q',
            'ҳ': 'h', 'Ў': 'O', 'Ғ': 'G',
            'Қ': 'Q', 'Ҳ': 'H', ' ': '-',
        }

        slug = name.lower()
        for old, new in replacements.items():
            slug = slug.replace(old, new)

        slug = ''.join(c if c.isalnum() or c == '-' else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))

        return slug[:255]
