from __future__ import annotations

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from taxonomy.models import Category

from ._seed_utils import resolve_resources_dir


CATEGORY_SPECS = [
    {
        "name": "Electronics",
        "name_ru": "Электроника",
        "name_uz": "Elektronika",
        "slug": "electronics",
        "icon": "electronics",
        "icon_file": "electronics_logo.png",
        "children": [
            ("Smartphones", "Смартфоны", "Smartfonlar", "smartphones"),
            ("Laptops", "Ноутбуки", "Noutbuklar", "laptops"),
            ("Tablets", "Планшеты", "Planshetlar", "tablets"),
            ("TV & Audio", "ТВ и аудио", "TV va audio", "tv-audio"),
        ],
    },
    {
        "name": "Vehicles",
        "name_ru": "Транспорт",
        "name_uz": "Transport",
        "slug": "vehicles",
        "icon": "vehicles",
        "icon_file": "car_logo.png",
        "children": [
            ("Cars", "Автомобили", "Avtomobillar", "cars"),
            ("Motorcycles", "Мотоциклы", "Mototsikllar", "motorcycles"),
            ("Auto Parts", "Автозапчасти", "Avto ehtiyot qismlar", "auto-parts"),
            ("Tires & Wheels", "Шины и диски", "Shina va disklar", "tires-wheels"),
        ],
    },
    {
        "name": "Real Estate",
        "name_ru": "Недвижимость",
        "name_uz": "Ko'chmas mulk",
        "slug": "real-estate",
        "icon": "real-estate",
        "icon_file": "house_logo.png",
        "children": [
            ("Apartments", "Квартиры", "Kvartiralar", "apartments"),
            ("Houses", "Дома", "Uylar", "houses"),
            ("Commercial", "Коммерческая недвижимость", "Tijorat ko'chmas mulki", "commercial"),
            ("Land", "Земельные участки", "Yer uchastkalari", "land"),
        ],
    },
    {
        "name": "Fashion",
        "name_ru": "Одежда",
        "name_uz": "Kiyim-kechak",
        "slug": "fashion",
        "icon": "fashion",
        "icon_file": "clothes_logo.png",
        "children": [
            ("Women's Clothing", "Женская одежда", "Ayollar kiyimi", "womens-clothing"),
            ("Men's Clothing", "Мужская одежда", "Erkaklar kiyimi", "mens-clothing"),
            ("Shoes", "Обувь", "Poyabzal", "shoes"),
            ("Accessories", "Аксессуары", "Aksessuarlar", "accessories"),
        ],
    },
    {
        "name": "Kids",
        "name_ru": "Детские товары",
        "name_uz": "Bolalar mahsulotlari",
        "slug": "kids",
        "icon": "kids",
        "icon_file": "bear_logo.png",
        "children": [
            ("Toys", "Игрушки", "O'yinchoqlar", "toys"),
            ("Baby Strollers", "Детские коляски", "Bolalar aravachalari", "baby-strollers"),
            ("Kids Clothing", "Детская одежда", "Bolalar kiyimi", "kids-clothing"),
            ("School Supplies", "Школьные товары", "Maktab anjomlari", "school-supplies"),
        ],
    },
]


class Command(BaseCommand):
    help = "Initialize product categories and subcategories using the shared resources icons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resources",
            type=str,
            default=None,
            help="Path to the shared resources directory or directly to category icon files.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing categories before inserting the seeded set.",
        )
        parser.add_argument(
            "--refresh-icons",
            action="store_true",
            help="Re-upload icon images even when a top-level category already has one.",
        )

    def handle(self, *args, **options):
        resources_dir = resolve_resources_dir(options.get("resources"))
        if not resources_dir:
            raise CommandError("Resources directory not found. Pass --resources with a valid path.")

        if options["clear"]:
            self.stdout.write("Clearing existing categories...")
            Category.objects.all().delete()

        created = 0
        updated = 0

        self.stdout.write(f"Using resources: {resources_dir}")

        for order, spec in enumerate(CATEGORY_SPECS, start=1):
            parent, parent_created, parent_updated = self._upsert_category(
                spec=spec,
                parent=None,
                order=order * 100,
            )
            created += int(parent_created)
            updated += int(parent_updated)

            icon_path = resources_dir / spec["icon_file"]
            if icon_path.exists() and (options["refresh_icons"] or not parent.icon_image):
                self._attach_icon_image(parent, icon_path)
            elif not icon_path.exists():
                self.stderr.write(f"Icon file missing for {parent.slug}: {icon_path}")

            for child_index, child in enumerate(spec["children"], start=1):
                child_spec = {
                    "name": child[0],
                    "name_ru": child[1],
                    "name_uz": child[2],
                    "slug": child[3],
                    "icon": "",
                }
                _, child_created, child_updated = self._upsert_category(
                    spec=child_spec,
                    parent=parent,
                    order=order * 100 + child_index,
                )
                created += int(child_created)
                updated += int(child_updated)

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories initialized (created: {created}, updated: {updated}, total: {Category.objects.count()})."
            )
        )

    def _upsert_category(
        self,
        *,
        spec: dict,
        parent: Category | None,
        order: int,
    ) -> tuple[Category, bool, bool]:
        category = Category.objects.filter(slug=spec["slug"]).first()
        created = category is None
        if category is None:
            category = Category(slug=spec["slug"])

        category_level = 0 if parent is None else parent.level + 1
        is_leaf = parent is not None

        changed = self._assign(category, "parent", parent)
        changed |= self._assign(category, "level", category_level)
        changed |= self._assign(category, "name", spec["name"])
        changed |= self._assign(category, "name_ru", spec.get("name_ru", ""))
        changed |= self._assign(category, "name_uz", spec.get("name_uz", ""))
        changed |= self._assign(category, "icon", spec.get("icon", ""))
        changed |= self._assign(category, "is_leaf", is_leaf)
        changed |= self._assign(category, "order", order)

        if created:
            category.save()
        elif changed:
            category.save(
                update_fields=[
                    "parent",
                    "level",
                    "name",
                    "name_ru",
                    "name_uz",
                    "icon",
                    "is_leaf",
                    "order",
                ]
            )

        return category, created, changed and not created

    def _assign(self, category: Category, field: str, value) -> bool:
        if getattr(category, field) == value:
            return False
        setattr(category, field, value)
        return True

    def _attach_icon_image(self, category: Category, path: Path):
        try:
            with path.open("rb") as handle:
                filename = f"{category.slug}{path.suffix.lower() or '.png'}"
                category.icon_image.save(filename, File(handle), save=True)
        except Exception as exc:  # pragma: no cover
            self.stderr.write(f"Failed to attach icon image for {category.name}: {exc}")
