from __future__ import annotations

from typing import Iterable, Tuple

from django.core.management.base import BaseCommand, CommandError

from taxonomy.models import Attribute, Category


class Command(BaseCommand):
    help = "Create common car-related attributes for the 'Cars' category (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category-id",
            type=int,
            default=None,
            help="Target category id. If omitted, will try to find a category whose name or slug contains 'car' (case-insensitive).",
        )

    def handle(self, *args, **options):
        cat = self._resolve_category(options.get("category_id"))
        if not cat:
            raise CommandError(
                "Cars category not found. Pass --category-id <id> or create a category first."
            )

        self.stdout.write(f"Using category: {cat.name} (id={cat.id}, slug={cat.slug})")

        created, updated = 0, 0
        for spec in self._car_attribute_specs():
            key, labels, typ, unit, options, is_required, min_number, max_number = spec
            obj, was_created = Attribute.objects.get_or_create(
                category=cat,
                key=key,
                defaults={
                    "label": labels.get("label", key.replace("_", " ").title()),
                    "label_ru": labels.get("ru", labels.get("label", "")),
                    "label_uz": labels.get("uz", labels.get("label", "")),
                    "type": typ,
                    "unit": unit,
                    "options": options or [],
                    "is_indexed": True,
                    "is_required": bool(is_required),
                    "min_number": min_number,
                    "max_number": max_number,
                },
            )
            if was_created:
                created += 1
            else:
                changed = False
                if obj.type != typ:
                    obj.type = typ; changed = True
                if (obj.unit or None) != unit:
                    obj.unit = unit; changed = True
                if (obj.options or []) != (options or []):
                    obj.options = options or []; changed = True
                if obj.is_required != bool(is_required):
                    obj.is_required = bool(is_required); changed = True
                if obj.min_number != min_number:
                    obj.min_number = min_number; changed = True
                if obj.max_number != max_number:
                    obj.max_number = max_number; changed = True
                if (obj.label_ru or "") != labels.get("ru", obj.label_ru or ""):
                    obj.label_ru = labels.get("ru", obj.label_ru or ""); changed = True
                if (obj.label_uz or "") != labels.get("uz", obj.label_uz or ""):
                    obj.label_uz = labels.get("uz", obj.label_uz or ""); changed = True
                if changed:
                    obj.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Car attributes done (created: {created}, updated: {updated})."))

    def _resolve_category(self, category_id: int | None) -> Category | None:
        if category_id:
            try:
                return Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return None
        qs = Category.objects.all()
        for field in ("name", "name_ru", "name_uz", "slug"):
            found = qs.filter(**{f"{field}__icontains": "car"}).order_by("level", "id").first()
            if found:
                return found
        for field, token in (("name_ru", "авто"), ("name_ru", "автомоб"), ("name_uz", "avto")):
            found = qs.filter(**{f"{field}__icontains": token}).order_by("level", "id").first()
            if found:
                return found
        return None

    def _car_attribute_specs(self) -> Iterable[Tuple[str, dict, str, str | None, list[str] | None, bool, float | None, float | None]]:
        return [
            ("brand", {"ru": "Марка", "uz": "Brend"}, "select", None, [
                "Chevrolet", "Hyundai", "Kia", "Toyota", "Volkswagen", "Honda", "Nissan"
            ], True, None, None),
            ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
            ("body_type", {"ru": "Тип кузова", "uz": "Kuzov turi"}, "select", None, [
                "Sedan", "Hatchback", "SUV", "Coupe", "Wagon", "Pickup"
            ], True, None, None),
            ("year", {"ru": "Год выпуска", "uz": "Ishlab chiqarilgan yil"}, "number", None, None, True, 1980, 2035),
            ("mileage", {"ru": "Пробег", "uz": "Yurgan masofa"}, "number", "km", None, False, 0, 2_000_000),
            ("transmission", {"ru": "Коробка передач", "uz": "Uzatmalar qutisi"}, "select", None, [
                "Manual", "Automatic", "CVT"
            ], False, None, None),
            ("fuel", {"ru": "Тип топлива", "uz": "Yoqilg‘i turi"}, "select", None, [
                "Petrol", "Diesel", "Hybrid", "Electric", "Gas"
            ], True, None, None),
            ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, [
                "White", "Black", "Silver", "Gray", "Blue", "Red", "Green"
            ], False, None, None),
            ("engine_volume", {"ru": "Объем двигателя", "uz": "Dvigatel hajmi"}, "number", "cm³", None, False, 200, 8000),
            ("owners_count", {"ru": "Количество владельцев", "uz": "Egalari soni"}, "number", None, None, False, 0, 10),
            ("options", {"ru": "Доп. опции", "uz": "Qo‘shimcha opsiyalar"}, "multiselect", None, [
                "A/C", "Heated seats", "Parking sensors", "Alarm", "Power windows"
            ], False, None, None),
        ]
