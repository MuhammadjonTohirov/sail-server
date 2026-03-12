from __future__ import annotations

from typing import Iterable

from django.core.management.base import BaseCommand, CommandError

from taxonomy.models import Attribute, Category


AttributeSpec = tuple[str, dict[str, str], str, str | None, list[str] | None, bool, float | None, float | None]


CATEGORY_ATTRIBUTE_SPECS: dict[str, list[AttributeSpec]] = {
    "smartphones": [
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "select", None, ["Apple", "Samsung", "Xiaomi", "Google", "Tecno", "Realme"], True, None, None),
        ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
        ("storage", {"ru": "Память", "uz": "Xotira"}, "select", "GB", ["64", "128", "256", "512", "1024"], True, None, None),
        ("ram", {"ru": "Оперативная память", "uz": "Tezkor xotira"}, "select", "GB", ["4", "6", "8", "12", "16"], False, None, None),
        ("screen_size", {"ru": "Диагональ экрана", "uz": "Ekran o'lchami"}, "number", "in", None, False, 4.0, 8.0),
        ("sim_type", {"ru": "SIM", "uz": "SIM turi"}, "select", None, ["Single SIM", "Dual SIM", "eSIM"], False, None, None),
    ],
    "laptops": [
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "select", None, ["Apple", "Dell", "Lenovo", "HP", "ASUS", "Acer"], True, None, None),
        ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
        ("processor", {"ru": "Процессор", "uz": "Protsessor"}, "text", None, None, True, None, None),
        ("ram", {"ru": "Оперативная память", "uz": "Tezkor xotira"}, "select", "GB", ["8", "16", "24", "32", "64"], True, None, None),
        ("storage", {"ru": "Накопитель", "uz": "Xotira"}, "select", "GB", ["256", "512", "1024", "2048"], True, None, None),
        ("screen_size", {"ru": "Диагональ экрана", "uz": "Ekran o'lchami"}, "number", "in", None, False, 11.0, 18.0),
    ],
    "tablets": [
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "select", None, ["Apple", "Samsung", "Lenovo", "Xiaomi", "Huawei"], True, None, None),
        ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
        ("storage", {"ru": "Память", "uz": "Xotira"}, "select", "GB", ["64", "128", "256", "512"], True, None, None),
        ("screen_size", {"ru": "Диагональ экрана", "uz": "Ekran o'lchami"}, "number", "in", None, False, 7.0, 15.0),
        ("connectivity", {"ru": "Связь", "uz": "Ulanish"}, "multiselect", None, ["Wi-Fi", "LTE", "5G", "Bluetooth"], False, None, None),
    ],
    "tv-audio": [
        ("item_type", {"ru": "Тип товара", "uz": "Mahsulot turi"}, "select", None, ["TV", "Soundbar", "Speaker", "Home Theater", "Projector"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "select", None, ["LG", "Samsung", "Sony", "JBL", "Hisense", "Artel"], True, None, None),
        ("screen_size", {"ru": "Диагональ", "uz": "Diagonal"}, "number", "in", None, False, 19.0, 100.0),
        ("smart_tv", {"ru": "Smart TV", "uz": "Smart TV"}, "boolean", None, None, False, None, None),
        ("ports", {"ru": "Порты и связь", "uz": "Portlar va aloqa"}, "multiselect", None, ["HDMI", "USB", "Bluetooth", "Wi-Fi", "Optical"], False, None, None),
    ],
    "cars": [
        ("brand", {"ru": "Марка", "uz": "Brend"}, "select", None, ["Chevrolet", "Hyundai", "Kia", "Toyota", "Volkswagen", "Honda", "Nissan"], True, None, None),
        ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
        ("body_type", {"ru": "Тип кузова", "uz": "Kuzov turi"}, "select", None, ["Sedan", "Hatchback", "SUV", "Coupe", "Wagon", "Pickup"], True, None, None),
        ("year", {"ru": "Год выпуска", "uz": "Ishlab chiqarilgan yil"}, "number", None, None, True, 1980, 2035),
        ("mileage", {"ru": "Пробег", "uz": "Yurgan masofa"}, "number", "km", None, False, 0, 2000000),
        ("transmission", {"ru": "Коробка передач", "uz": "Uzatmalar qutisi"}, "select", None, ["Manual", "Automatic", "CVT"], False, None, None),
        ("fuel", {"ru": "Тип топлива", "uz": "Yoqilg'i turi"}, "select", None, ["Petrol", "Diesel", "Hybrid", "Electric", "Gas"], True, None, None),
        ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, ["White", "Black", "Silver", "Gray", "Blue", "Red", "Green"], False, None, None),
        ("engine_volume", {"ru": "Объем двигателя", "uz": "Dvigatel hajmi"}, "number", "cm³", None, False, 200, 8000),
        ("owners_count", {"ru": "Количество владельцев", "uz": "Egalari soni"}, "number", None, None, False, 0, 10),
        ("options", {"ru": "Доп. опции", "uz": "Qo'shimcha opsiyalar"}, "multiselect", None, ["A/C", "Heated seats", "Parking sensors", "Alarm", "Power windows"], False, None, None),
    ],
    "motorcycles": [
        ("brand", {"ru": "Марка", "uz": "Brend"}, "select", None, ["Honda", "Yamaha", "Suzuki", "Lifan", "Bajaj", "Kawasaki"], True, None, None),
        ("model", {"ru": "Модель", "uz": "Model"}, "text", None, None, True, None, None),
        ("year", {"ru": "Год выпуска", "uz": "Ishlab chiqarilgan yil"}, "number", None, None, True, 1980, 2035),
        ("mileage", {"ru": "Пробег", "uz": "Yurgan masofa"}, "number", "km", None, False, 0, 500000),
        ("engine_volume", {"ru": "Объем двигателя", "uz": "Dvigatel hajmi"}, "number", "cm³", None, True, 50, 2500),
        ("starter_type", {"ru": "Тип запуска", "uz": "Ishga tushirish turi"}, "select", None, ["Electric", "Kick", "Both"], False, None, None),
    ],
    "auto-parts": [
        ("part_type", {"ru": "Тип детали", "uz": "Ehtiyot qism turi"}, "select", None, ["Body", "Engine", "Suspension", "Electrical", "Interior", "Optics"], True, None, None),
        ("vehicle_brand", {"ru": "Марка авто", "uz": "Avto brendi"}, "select", None, ["Chevrolet", "Hyundai", "Kia", "Toyota", "BYD", "Other"], False, None, None),
        ("part_number", {"ru": "Номер детали", "uz": "Detal raqami"}, "text", None, None, False, None, None),
        ("is_original", {"ru": "Оригинал", "uz": "Original"}, "boolean", None, None, False, None, None),
        ("compatibility", {"ru": "Совместимость", "uz": "Mosligi"}, "text", None, None, False, None, None),
    ],
    "tires-wheels": [
        ("item_type", {"ru": "Тип", "uz": "Turi"}, "select", None, ["Tire", "Wheel", "Set"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "select", None, ["Michelin", "Kumho", "Pirelli", "Yokohama", "Artmotion", "Other"], False, None, None),
        ("diameter", {"ru": "Диаметр", "uz": "Diametr"}, "number", "in", None, True, 12, 24),
        ("season", {"ru": "Сезон", "uz": "Mavsum"}, "select", None, ["Summer", "Winter", "All Season"], False, None, None),
        ("quantity", {"ru": "Количество", "uz": "Soni"}, "number", None, None, True, 1, 8),
        ("width", {"ru": "Ширина", "uz": "Kengligi"}, "number", "mm", None, False, 100, 400),
    ],
    "apartments": [
        ("rooms", {"ru": "Комнаты", "uz": "Xonalar"}, "number", None, None, True, 1, 20),
        ("area_sqm", {"ru": "Площадь", "uz": "Maydon"}, "number", "m²", None, True, 10, 2000),
        ("floor", {"ru": "Этаж", "uz": "Qavat"}, "number", None, None, False, 1, 100),
        ("total_floors", {"ru": "Этажность дома", "uz": "Uy qavatlari"}, "number", None, None, False, 1, 100),
        ("renovation", {"ru": "Ремонт", "uz": "Ta'mir"}, "select", None, ["Needs renovation", "Basic", "Good", "Designer"], False, None, None),
        ("furnished", {"ru": "С мебелью", "uz": "Mebelli"}, "boolean", None, None, False, None, None),
    ],
    "houses": [
        ("rooms", {"ru": "Комнаты", "uz": "Xonalar"}, "number", None, None, True, 1, 30),
        ("house_area_sqm", {"ru": "Площадь дома", "uz": "Uy maydoni"}, "number", "m²", None, True, 20, 5000),
        ("land_area_sotix", {"ru": "Площадь участка", "uz": "Yer maydoni"}, "number", "sotix", None, False, 1, 500),
        ("floors", {"ru": "Этажей", "uz": "Qavatlar soni"}, "number", None, None, False, 1, 10),
        ("utilities", {"ru": "Коммуникации", "uz": "Kommunikatsiyalar"}, "multiselect", None, ["Gas", "Water", "Electricity", "Sewerage", "Internet"], False, None, None),
        ("renovation", {"ru": "Ремонт", "uz": "Ta'mir"}, "select", None, ["Needs renovation", "Basic", "Good", "Designer"], False, None, None),
    ],
    "commercial": [
        ("property_type", {"ru": "Тип объекта", "uz": "Obyekt turi"}, "select", None, ["Office", "Shop", "Warehouse", "Cafe", "Beauty salon", "Production"], True, None, None),
        ("area_sqm", {"ru": "Площадь", "uz": "Maydon"}, "number", "m²", None, True, 10, 10000),
        ("floor", {"ru": "Этаж", "uz": "Qavat"}, "number", None, None, False, 1, 100),
        ("parking", {"ru": "Парковка", "uz": "Avtoturargoh"}, "boolean", None, None, False, None, None),
        ("ready_business", {"ru": "Готовый бизнес", "uz": "Tayyor biznes"}, "boolean", None, None, False, None, None),
    ],
    "land": [
        ("land_area_sotix", {"ru": "Площадь участка", "uz": "Yer maydoni"}, "number", "sotix", None, True, 1, 10000),
        ("purpose", {"ru": "Назначение", "uz": "Maqsadi"}, "select", None, ["Residential", "Commercial", "Agricultural", "Industrial"], True, None, None),
        ("cadastral", {"ru": "Кадастр есть", "uz": "Kadastr bor"}, "boolean", None, None, False, None, None),
        ("road_access", {"ru": "Подъездная дорога", "uz": "Yo'l mavjud"}, "boolean", None, None, False, None, None),
        ("utilities", {"ru": "Коммуникации", "uz": "Kommunikatsiyalar"}, "multiselect", None, ["Gas", "Water", "Electricity", "Internet"], False, None, None),
    ],
    "womens-clothing": [
        ("item_type", {"ru": "Тип одежды", "uz": "Kiyim turi"}, "select", None, ["Dress", "Blouse", "Jacket", "Jeans", "Coat", "Suit"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("size", {"ru": "Размер", "uz": "O'lcham"}, "select", None, ["XS", "S", "M", "L", "XL", "XXL"], True, None, None),
        ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, ["Black", "White", "Beige", "Blue", "Red", "Green"], False, None, None),
        ("season", {"ru": "Сезон", "uz": "Mavsum"}, "multiselect", None, ["Spring", "Summer", "Autumn", "Winter"], False, None, None),
    ],
    "mens-clothing": [
        ("item_type", {"ru": "Тип одежды", "uz": "Kiyim turi"}, "select", None, ["T-shirt", "Shirt", "Jacket", "Jeans", "Suit", "Coat"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("size", {"ru": "Размер", "uz": "O'lcham"}, "select", None, ["S", "M", "L", "XL", "XXL", "XXXL"], True, None, None),
        ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, ["Black", "White", "Blue", "Gray", "Brown", "Green"], False, None, None),
        ("season", {"ru": "Сезон", "uz": "Mavsum"}, "multiselect", None, ["Spring", "Summer", "Autumn", "Winter"], False, None, None),
    ],
    "shoes": [
        ("shoe_type", {"ru": "Тип обуви", "uz": "Oyoq kiyim turi"}, "select", None, ["Sneakers", "Classic", "Boots", "Sandals", "Loafers"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("size", {"ru": "Размер", "uz": "O'lcham"}, "number", "EU", None, True, 18, 50),
        ("material", {"ru": "Материал", "uz": "Material"}, "select", None, ["Leather", "Eco leather", "Textile", "Suede", "Rubber"], False, None, None),
        ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, ["Black", "White", "Brown", "Blue", "Gray"], False, None, None),
    ],
    "accessories": [
        ("item_type", {"ru": "Тип аксессуара", "uz": "Aksessuar turi"}, "select", None, ["Watch", "Bag", "Backpack", "Wallet", "Jewelry", "Sunglasses"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("material", {"ru": "Материал", "uz": "Material"}, "select", None, ["Leather", "Textile", "Metal", "Plastic", "Gold plated"], False, None, None),
        ("color", {"ru": "Цвет", "uz": "Rang"}, "select", None, ["Black", "Brown", "White", "Silver", "Gold"], False, None, None),
        ("for_gender", {"ru": "Для кого", "uz": "Kim uchun"}, "select", None, ["Women", "Men", "Unisex"], False, None, None),
    ],
    "toys": [
        ("toy_type", {"ru": "Тип игрушки", "uz": "O'yinchoq turi"}, "select", None, ["Educational", "Soft toy", "RC toy", "Board game", "Blocks"], True, None, None),
        ("age_group", {"ru": "Возраст", "uz": "Yosh guruhi"}, "select", None, ["0-1", "1-3", "3-5", "5-8", "8+"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("material", {"ru": "Материал", "uz": "Material"}, "select", None, ["Plastic", "Wood", "Fabric", "Rubber"], False, None, None),
        ("battery_required", {"ru": "Нужны батарейки", "uz": "Batareya kerak"}, "boolean", None, None, False, None, None),
    ],
    "baby-strollers": [
        ("stroller_type", {"ru": "Тип коляски", "uz": "Aravacha turi"}, "select", None, ["Walking", "2-in-1", "3-in-1", "Travel", "Twins"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("age_group", {"ru": "Возраст ребенка", "uz": "Bola yoshi"}, "select", None, ["0-6 months", "6-12 months", "1-3 years"], False, None, None),
        ("folding_mechanism", {"ru": "Складной механизм", "uz": "Buklanadigan mexanizm"}, "boolean", None, None, False, None, None),
        ("weight_kg", {"ru": "Вес", "uz": "Og'irligi"}, "number", "kg", None, False, 3, 40),
    ],
    "kids-clothing": [
        ("item_type", {"ru": "Тип одежды", "uz": "Kiyim turi"}, "select", None, ["Set", "Jacket", "Shirt", "Pants", "School uniform"], True, None, None),
        ("size", {"ru": "Размер", "uz": "O'lcham"}, "select", None, ["50-56", "62-68", "74-80", "86-92", "98-104", "110-116", "122-128"], True, None, None),
        ("age_group", {"ru": "Возраст", "uz": "Yosh guruhi"}, "select", None, ["0-1", "1-3", "3-5", "5-8", "8-12"], False, None, None),
        ("gender", {"ru": "Пол", "uz": "Jinsi"}, "select", None, ["Boy", "Girl", "Unisex"], False, None, None),
        ("season", {"ru": "Сезон", "uz": "Mavsum"}, "multiselect", None, ["Spring", "Summer", "Autumn", "Winter"], False, None, None),
    ],
    "school-supplies": [
        ("item_type", {"ru": "Тип товара", "uz": "Mahsulot turi"}, "select", None, ["Backpack", "Stationery", "Notebook", "Desk", "Art supplies"], True, None, None),
        ("brand", {"ru": "Бренд", "uz": "Brend"}, "text", None, None, False, None, None),
        ("age_group", {"ru": "Возраст", "uz": "Yosh guruhi"}, "select", None, ["Preschool", "Primary school", "Middle school", "High school"], False, None, None),
        ("quantity", {"ru": "Количество", "uz": "Soni"}, "number", None, None, False, 1, 1000),
        ("material", {"ru": "Материал", "uz": "Material"}, "text", None, None, False, None, None),
    ],
}


class Command(BaseCommand):
    help = "Create category-specific attributes for the generated mock taxonomy (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category-slug",
            action="append",
            dest="category_slugs",
            help="Seed only the specified category slug. Can be passed multiple times.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing attributes for the targeted categories before recreating them.",
        )

    def handle(self, *args, **options):
        requested_slugs = options.get("category_slugs") or []
        target_slugs = requested_slugs or list(CATEGORY_ATTRIBUTE_SPECS.keys())

        categories = {category.slug: category for category in Category.objects.filter(slug__in=target_slugs)}
        missing = [slug for slug in target_slugs if slug not in categories]
        if missing:
            raise CommandError(
                "Missing categories for attribute setup: "
                + ", ".join(missing)
                + ". Run `python3 manage.py init_categories` first."
            )

        created = 0
        updated = 0
        cleared = 0

        for slug in target_slugs:
            category = categories[slug]
            specs = CATEGORY_ATTRIBUTE_SPECS[slug]

            if options["clear"]:
                deleted_count, _ = Attribute.objects.filter(category=category).delete()
                cleared += deleted_count

            c_created, c_updated = self._sync_category_attributes(category, specs)
            created += c_created
            updated += c_updated
            self.stdout.write(
                f"{category.slug}: created {c_created}, updated {c_updated}, total {Attribute.objects.filter(category=category).count()}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Category attributes ready (created: {created}, updated: {updated}, cleared: {cleared})."
            )
        )

    def _sync_category_attributes(self, category: Category, specs: Iterable[AttributeSpec]) -> tuple[int, int]:
        created = 0
        updated = 0

        for key, labels, attr_type, unit, options, is_required, min_number, max_number in specs:
            attribute, was_created = Attribute.objects.get_or_create(
                category=category,
                key=key,
                defaults={
                    "label": labels.get("label", labels.get("ru", key.replace("_", " ").title())),
                    "label_ru": labels.get("ru", ""),
                    "label_uz": labels.get("uz", ""),
                    "type": attr_type,
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
                continue

            changed = False
            changed |= self._assign(attribute, "label", labels.get("label", labels.get("ru", attribute.label)))
            changed |= self._assign(attribute, "label_ru", labels.get("ru", ""))
            changed |= self._assign(attribute, "label_uz", labels.get("uz", ""))
            changed |= self._assign(attribute, "type", attr_type)
            changed |= self._assign(attribute, "unit", unit)
            changed |= self._assign(attribute, "options", options or [])
            changed |= self._assign(attribute, "is_indexed", True)
            changed |= self._assign(attribute, "is_required", bool(is_required))
            changed |= self._assign(attribute, "min_number", min_number)
            changed |= self._assign(attribute, "max_number", max_number)

            if changed:
                attribute.save(
                    update_fields=[
                        "label",
                        "label_ru",
                        "label_uz",
                        "type",
                        "unit",
                        "options",
                        "is_indexed",
                        "is_required",
                        "min_number",
                        "max_number",
                    ]
                )
                updated += 1

        return created, updated

    def _assign(self, instance, field: str, value) -> bool:
        if getattr(instance, field) == value:
            return False
        setattr(instance, field, value)
        return True
