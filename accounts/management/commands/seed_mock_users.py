from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.mock_seed import MOCK_EMAIL_DOMAIN, build_mock_user_specs
from accounts.models import Profile
from taxonomy.models import Location


class Command(BaseCommand):
    help = "Generate mock users, export their credentials, and store them in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="How many mock users to create.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="mock_data/generated_users.json",
            help="Relative or absolute path for the exported credentials JSON.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously generated mock users before recreating them.",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count <= 0:
            raise CommandError("--count must be greater than 0.")

        regions = list(Location.objects.filter(kind=Location.Kind.REGION).order_by("id"))
        if not regions:
            raise CommandError(
                "No regions found. Run `python3 manage.py import_locations` before seeding users."
            )

        User = get_user_model()

        if options["clear"]:
            self.stdout.write("Clearing previously generated mock users...")
            User.objects.filter(username__iendswith=f"@{MOCK_EMAIL_DOMAIN}").delete()

        specs = build_mock_user_specs(count)
        output_rows: list[dict] = []
        created = 0
        updated = 0

        for index, spec in enumerate(specs):
            region = regions[index % len(regions)]
            user, was_created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "is_active": True,
                },
            )

            changed = False
            changed |= self._assign(user, "email", spec["email"])
            changed |= self._assign(user, "first_name", spec["first_name"])
            changed |= self._assign(user, "last_name", spec["last_name"])
            changed |= self._assign(user, "is_active", True)
            user.set_password(spec["password"])

            if was_created:
                user.save()
                created += 1
            else:
                user.save(update_fields=["email", "first_name", "last_name", "is_active", "password"])
                updated += int(changed or True)

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.display_name = spec["display_name"]
            profile.phone_e164 = spec["phone_e164"]
            profile.email = spec["email"]
            profile.avatar_url = spec["avatar_url"]
            profile.about = spec["about"]
            profile.location = region
            profile.last_active_at = timezone.now() - timedelta(days=index % 6, hours=index % 12)
            profile.save()

            output_rows.append(
                {
                    "user_id": user.id,
                    "login": spec["login"],
                    "password": spec["password"],
                    "email": spec["email"],
                    "phone_e164": spec["phone_e164"],
                    "display_name": spec["display_name"],
                    "location_id": region.id,
                    "location_name": region.name_uz or region.name,
                }
            )

        output_path = self._resolve_output_path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_rows, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock users seeded (created: {created}, updated: {updated}, exported: {len(output_rows)})."
            )
        )
        self.stdout.write(f"Credentials file: {output_path}")

    def _resolve_output_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        return (settings.BASE_DIR / path).resolve()

    def _assign(self, instance, field: str, value) -> bool:
        if getattr(instance, field) == value:
            return False
        setattr(instance, field, value)
        return True
