"""
Django management command to import Uzbekistan regions and districts data.

Usage:
    python manage.py import_locations
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from taxonomy.models import Location


class Command(BaseCommand):
    help = 'Import Uzbekistan regions and districts from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='resources/uzbekistan-regions-data-master/JSON',
            help='Path to the directory containing regions.json and districts.json'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing location data before import'
        )

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])

        if not data_dir.exists():
            self.stdout.write(self.style.ERROR(f'Data directory not found: {data_dir}'))
            return

        regions_file = data_dir / 'regions.json'
        districts_file = data_dir / 'districts.json'

        if not regions_file.exists():
            self.stdout.write(self.style.ERROR(f'Regions file not found: {regions_file}'))
            return

        if not districts_file.exists():
            self.stdout.write(self.style.ERROR(f'Districts file not found: {districts_file}'))
            return

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing location data...')
            Location.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing data'))

        try:
            with transaction.atomic():
                # Create Uzbekistan as country
                uzbekistan, created = Location.objects.get_or_create(
                    kind=Location.Kind.COUNTRY,
                    name='Uzbekistan',
                    defaults={
                        'name_ru': 'Узбекистан',
                        'name_uz': 'O\'zbekiston',
                        'slug': 'uzbekistan',
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Uzbekistan country'))

                # Import regions
                self.stdout.write('Importing regions...')
                with open(regions_file, 'r', encoding='utf-8-sig') as f:
                    regions_data = json.load(f)

                region_map = {}  # Map original ID to Location object
                for region in regions_data:
                    location, created = Location.objects.get_or_create(
                        kind=Location.Kind.REGION,
                        parent=uzbekistan,
                        name=region['name_uz'],
                        defaults={
                            'name_ru': region.get('name_ru', ''),
                            'name_uz': region.get('name_uz', ''),
                            'slug': self._make_slug(region['name_uz']),
                        }
                    )
                    region_map[region['id']] = location

                    if created:
                        self.stdout.write(f'  ✓ Created region: {location.name}')

                self.stdout.write(self.style.SUCCESS(f'✓ Imported {len(regions_data)} regions'))

                # Import districts
                self.stdout.write('Importing districts...')
                with open(districts_file, 'r', encoding='utf-8-sig') as f:
                    districts_data = json.load(f)

                district_count = 0
                city_count = 0

                for district in districts_data:
                    region_id = district.get('region_id')
                    parent_location = region_map.get(region_id)

                    if not parent_location:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Skipping {district["name_uz"]} - parent region not found')
                        )
                        continue

                    # Determine if it's a city or district based on SOATO
                    # Cities typically have SOATO ending in 401, 403, etc.
                    soato_str = str(district.get('soato_id', ''))
                    is_city = soato_str[-3:].startswith('4')

                    kind = Location.Kind.CITY if is_city else Location.Kind.DISTRICT

                    location, created = Location.objects.get_or_create(
                        kind=kind,
                        parent=parent_location,
                        name=district['name_uz'],
                        defaults={
                            'name_ru': district.get('name_ru', ''),
                            'name_uz': district.get('name_uz', ''),
                            'slug': self._make_slug(district['name_uz']),
                        }
                    )

                    if created:
                        if is_city:
                            city_count += 1
                        else:
                            district_count += 1

                self.stdout.write(self.style.SUCCESS(
                    f'✓ Imported {district_count} districts and {city_count} cities'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Successfully imported all location data!'
                ))
                self.stdout.write(f'   Total locations: {Location.objects.count()}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error importing data: {str(e)}'))
            raise

    def _make_slug(self, name):
        """Create a slug from Uzbek/Russian text"""
        # Simple transliteration for common Uzbek/Russian characters
        replacements = {
            'ʻ': '', "'": '', '\'': '',
            'ў': 'o', 'ғ': 'g', 'қ': 'q',
            'ҳ': 'h', 'Ў': 'O', 'Ғ': 'G',
            'Қ': 'Q', 'Ҳ': 'H',
        }

        slug = name.lower()
        for old, new in replacements.items():
            slug = slug.replace(old, new)

        # Remove special characters and replace spaces
        slug = ''.join(c if c.isalnum() or c in '-_' else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))  # Remove duplicate dashes

        return slug[:255]  # Ensure it fits in the field
