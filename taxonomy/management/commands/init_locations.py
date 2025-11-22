from __future__ import annotations

from django.core.management.base import BaseCommand

from taxonomy.models import Location


class Command(BaseCommand):
    help = "Initialize Uzbekistan regions and main cities (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write("Initializing locations…")

        country, _ = Location.objects.get_or_create(name="Uzbekistan", kind=Location.Kind.COUNTRY)

        regions = [
            ("Tashkent Region", [("Tashkent", 41.3111, 69.2797)]),
            ("Samarkand Region", [("Samarkand", 39.6542, 66.9597)]),
            ("Andijan Region", [("Andijan", 40.7821, 72.3442)]),
            ("Bukhara Region", [("Bukhara", 39.7747, 64.4286)]),
            ("Namangan Region", [("Namangan", 40.9983, 71.6726)]),
            ("Fergana Region", [("Fergana", 40.3734, 71.7979)]),
            ("Khorezm Region", [("Urgench", 41.5535, 60.6206)]),
            ("Kashkadarya Region", [("Karshi", 38.8606, 65.7847)]),
            ("Surxondaryo Region", [("Termez", 37.2246, 67.2783)]),
            ("Karakalpakstan", [("Nukus", 42.4602, 59.6100)]),
        ]

        created = 0
        for rname, cities in regions:
            region, rc = Location.objects.get_or_create(name=rname, kind=Location.Kind.REGION, parent=country)
            created += int(rc)
            for cname, lat, lon in cities:
                _, cc = Location.objects.get_or_create(
                    name=cname, kind=Location.Kind.CITY, parent=region, defaults={"lat": lat, "lon": lon}
                )
                created += int(cc)

        self.stdout.write(self.style.SUCCESS(f"Locations initialized (created {created})."))

