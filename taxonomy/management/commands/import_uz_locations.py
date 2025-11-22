"""
Django management command to import complete Uzbekistan location hierarchy.

Data structure:
- Country: Uzbekistan
- Regions: 14 regions (viloyat)
- Districts: Districts within each region (tuman)
- Villages: Villages within districts (optional for UI)
- Quarters: City quarters (optional for UI)

For the location picker, we'll only use Region → District to keep UX simple.

Usage:
    python manage.py import_uz_locations --clear
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from taxonomy.models import Location


class Command(BaseCommand):
    help = 'Import Uzbekistan complete location hierarchy from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='resources/uzbekistan-regions-data-master/JSON',
            help='Path to the directory containing JSON files'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing location data before import'
        )
        parser.add_argument(
            '--districts-only',
            action='store_true',
            help='Only import regions and districts (skip villages/quarters for simpler UI)'
        )

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])

        if not data_dir.exists():
            self.stdout.write(self.style.ERROR(f'Data directory not found: {data_dir}'))
            return

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing location data...')
            Location.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing data'))

        try:
            with transaction.atomic():
                # 1. Create Uzbekistan as country
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

                # 2. Import regions
                regions_file = data_dir / 'regions.json'
                if not regions_file.exists():
                    self.stdout.write(self.style.ERROR(f'regions.json not found'))
                    return

                self.stdout.write('Importing regions...')
                with open(regions_file, 'r', encoding='utf-8-sig') as f:
                    regions_data = json.load(f)

                region_map = {}
                for region in regions_data:
                    # Use name_uz as primary, it's cleaner
                    location, created = Location.objects.get_or_create(
                        kind='REGION',
                        parent=uzbekistan,
                        name_uz=region['name_uz'],
                        defaults={
                            'name': region['name_uz'],
                            'name_ru': region.get('name_ru', ''),
                            'slug': self._make_slug(region['name_uz']),
                        }
                    )
                    region_map[region['id']] = location
                    if created:
                        self.stdout.write(f'  ✓ {location.name_uz}')

                self.stdout.write(self.style.SUCCESS(f'✓ Imported {len(region_map)} regions\n'))

                # 3. Import districts
                districts_file = data_dir / 'districts.json'
                if not districts_file.exists():
                    self.stdout.write(self.style.ERROR(f'districts.json not found'))
                    return

                self.stdout.write('Importing districts...')
                with open(districts_file, 'r', encoding='utf-8-sig') as f:
                    districts_data = json.load(f)

                district_map = {}
                for district in districts_data:
                    region_id = district.get('region_id')
                    parent_location = region_map.get(region_id)

                    if not parent_location:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Skipping {district["name_uz"]} - parent not found')
                        )
                        continue

                    location, created = Location.objects.get_or_create(
                        kind='DISTRICT',
                        parent=parent_location,
                        name_uz=district['name_uz'],
                        defaults={
                            'name': district['name_uz'],
                            'name_ru': district.get('name_ru', ''),
                            'slug': self._make_slug(district['name_uz']),
                        }
                    )
                    district_map[district['id']] = location

                self.stdout.write(self.style.SUCCESS(f'✓ Imported {len(district_map)} districts\n'))

                # 4. Optionally import villages (for detailed location data)
                if not options['districts_only']:
                    villages_file = data_dir / 'villages.json'
                    if villages_file.exists():
                        self.stdout.write('Importing villages...')
                        with open(villages_file, 'r', encoding='utf-8-sig') as f:
                            villages_data = json.load(f)

                        village_count = 0
                        for village in villages_data:
                            district_id = village.get('district_id')
                            parent_location = district_map.get(district_id)

                            if not parent_location:
                                continue

                            _, created = Location.objects.get_or_create(
                                kind='VILLAGE',
                                parent=parent_location,
                                name_uz=village['name_uz'],
                                defaults={
                                    'name': village['name_uz'],
                                    'name_ru': village.get('name_ru', ''),
                                    'slug': self._make_slug(village['name_uz']),
                                }
                            )
                            if created:
                                village_count += 1

                        self.stdout.write(self.style.SUCCESS(f'✓ Imported {village_count} villages\n'))

                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Import complete! Total locations: {Location.objects.count()}'
                ))
                self.stdout.write(f'   - Regions: {Location.objects.filter(kind="REGION").count()}')
                self.stdout.write(f'   - Districts: {Location.objects.filter(kind="DISTRICT").count()}')
                if not options['districts_only']:
                    self.stdout.write(f'   - Villages: {Location.objects.filter(kind="VILLAGE").count()}')

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

        # Keep only alphanumeric and dashes
        slug = ''.join(c if c.isalnum() or c == '-' else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))  # Remove duplicate dashes

        return slug[:255]
