from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from taxonomy.models import Category


class Command(BaseCommand):
    help = "Initialize default categories with subcategories (total 10). Optionally attaches a default icon image from a resources folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resources",
            type=str,
            default=None,
            help="Path to resources folder containing a default category icon image (e.g., category.png). If omitted, common locations will be probed.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Initializing categories…")

        data = [
            {"name": "Electronics", "icon": "📱", "order": 10, "children": ["Phones"]},
            {"name": "Vehicles", "icon": "🚗", "order": 20, "children": ["Cars"]},
            {"name": "Real Estate", "icon": "🏠", "order": 30, "children": ["Apartments"]},
            {"name": "Home & Garden", "icon": "🛋️", "order": 40, "children": ["Furniture"]},
            {"name": "Jobs", "icon": "💼", "order": 50, "children": ["Vacancies"]},
        ]

        default_icon_path = self._find_default_icon(options.get("resources"))
        if default_icon_path:
            self.stdout.write(self.style.NOTICE(f"Using default icon image: {default_icon_path}"))
        else:
            self.stdout.write("No default icon image found; proceeding without images.")

        created_count = 0
        for item in data:
            parent, created = Category.objects.get_or_create(
                name=item["name"], defaults={"is_leaf": False, "order": item.get("order", 0), "icon": item.get("icon", "")}
            )
            # attach default icon image to top-level categories (if missing)
            if default_icon_path and not parent.icon_image:
                self._attach_icon_image(parent, default_icon_path)
            created_count += int(created)

            # ensure level and leaf flags are sane
            if parent.level != 0:
                parent.level = 0
                parent.save(update_fields=["level"])

            for idx, child_name in enumerate(item.get("children", []), start=1):
                child, ccreated = Category.objects.get_or_create(
                    name=child_name, defaults={"parent": parent, "is_leaf": True, "order": item.get("order", 0) + idx}
                )
                if child.parent_id != parent.id:
                    child.parent = parent
                    child.save(update_fields=["parent"])
                if not child.is_leaf:
                    child.is_leaf = True
                    child.save(update_fields=["is_leaf"])
                created_count += int(ccreated)

        self.stdout.write(self.style.SUCCESS(f"Categories initialized (created {created_count}, total {Category.objects.count()})."))

    def _find_default_icon(self, explicit: str | None) -> Path | None:
        candidates: list[Path] = []
        if explicit:
            p = Path(explicit)
            if p.is_dir():
                candidates.append(p)
            elif p.is_file():
                return p
        base = Path(settings.BASE_DIR)
        candidates.extend([
            base.parent / "resources",
            base / "resources",
        ])
        filenames = [
            "category.png",
            "category_default.png",
            "default_category.png",
            "default.png",
            "icon.png",
        ]
        for folder in candidates:
            if not folder.exists():
                continue
            for name in filenames:
                f = folder / name
                if f.exists():
                    return f
            for ext in ("png", "jpg", "jpeg", "webp"):
                imgs = list(folder.glob(f"*.{ext}"))
                if imgs:
                    return imgs[0]
        return None

    def _attach_icon_image(self, category: Category, path: Path):
        try:
            with open(path, "rb") as fh:
                filename = f"{category.slug or category.name}.png"
                category.icon_image.save(filename, File(fh), save=True)
        except Exception as e:  # pragma: no cover
            self.stderr.write(f"Failed to attach icon image for {category.name}: {e}")

