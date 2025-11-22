from django.core.management.base import BaseCommand

from taxonomy.models import Attribute, Category, Location


class Command(BaseCommand):
    help = "Seed sample categories, attributes, and locations for development"

    def handle(self, *args, **options):
        self.stdout.write("Seeding taxonomy...")
        # Locations
        uz, _ = Location.objects.get_or_create(name="Uzbekistan", kind=Location.Kind.COUNTRY)
        tash_region, _ = Location.objects.get_or_create(
            name="Tashkent Region", kind=Location.Kind.REGION, parent=uz
        )
        tashkent, _ = Location.objects.get_or_create(
            name="Tashkent", kind=Location.Kind.CITY, parent=tash_region, lat=41.3111, lon=69.2797
        )
        # Categories
        vehicles, _ = Category.objects.get_or_create(name="Vehicles", level=0, is_leaf=False, order=10)
        cars, _ = Category.objects.get_or_create(name="Cars", parent=vehicles, level=1, is_leaf=False, order=10)
        sedans, _ = Category.objects.get_or_create(name="Sedans", parent=cars, level=2, is_leaf=True, order=10)

        electronics, _ = Category.objects.get_or_create(name="Electronics", level=0, is_leaf=False, order=20)
        phones, _ = Category.objects.get_or_create(name="Phones", parent=electronics, level=1, is_leaf=True, order=10)

        # Attributes for cars
        for key, label, typ, unit, options, required, min_n, max_n in [
            ("brand", "Brand", "select", None, ["Chevrolet", "Hyundai", "Kia", "Toyota"], True, None, None),
            ("year", "Year", "number", None, [], True, 1980, 2030),
            ("mileage", "Mileage", "number", "km", [], False, 0, 1000000),
            ("transmission", "Transmission", "select", None, ["Manual", "Automatic"], False, None, None),
        ]:
            Attribute.objects.get_or_create(
                category=cars,
                key=key,
                defaults={
                    "label": label,
                    "type": typ,
                    "unit": unit,
                    "options": options,
                    "is_indexed": True,
                    "is_required": required,
                    "min_number": min_n,
                    "max_number": max_n,
                },
            )

        # Attributes for phones
        for key, label, typ, unit, options, required in [
            ("brand", "Brand", "select", None, ["Apple", "Samsung", "Xiaomi", "Realme"], True),
            ("storage", "Storage", "select", "GB", ["64", "128", "256", "512"], True),
            ("condition", "Condition", "select", None, ["New", "Used"], True),
        ]:
            Attribute.objects.get_or_create(
                category=phones,
                key=key,
                defaults={
                    "label": label,
                    "type": typ,
                    "unit": unit,
                    "options": options,
                    "is_indexed": True,
                    "is_required": required,
                },
            )

        self.stdout.write(self.style.SUCCESS("Taxonomy seeding complete."))
