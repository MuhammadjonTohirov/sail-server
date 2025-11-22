from decimal import Decimal

from django.core.management.base import BaseCommand

from currency.models import Currency, ExchangeRate


class Command(BaseCommand):
    help = "Setup default currencies (USD, UZS) and exchange rates"

    def handle(self, *args, **options):
        self.stdout.write("Setting up currencies and exchange rates...")

        # Create USD currency
        usd, created = Currency.objects.get_or_create(
            code="USD",
            defaults={
                "name": "US Dollar",
                "symbol": "$",
                "is_active": True,
                "is_default": False,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created currency: {usd}"))
        else:
            self.stdout.write(f"Currency already exists: {usd}")

        # Create UZS currency (default)
        uzs, created = Currency.objects.get_or_create(
            code="UZS",
            defaults={
                "name": "Uzbek Sum",
                "symbol": "so'm",
                "is_active": True,
                "is_default": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created currency: {uzs}"))
        else:
            self.stdout.write(f"Currency already exists: {uzs}")

        # Create exchange rates
        # 1 USD = 12,195.20 UZS
        usd_to_uzs_rate = Decimal("12195.20")
        uzs_to_usd_rate = Decimal("1") / usd_to_uzs_rate

        # USD to UZS
        rate1, created = ExchangeRate.objects.get_or_create(
            from_currency=usd,
            to_currency=uzs,
            defaults={"rate": usd_to_uzs_rate, "is_active": True},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created exchange rate: {rate1}"))
        else:
            # Update existing rate
            if rate1.rate != usd_to_uzs_rate:
                rate1.rate = usd_to_uzs_rate
                rate1.save()
                self.stdout.write(self.style.SUCCESS(f"Updated exchange rate: {rate1}"))
            else:
                self.stdout.write(f"Exchange rate already exists: {rate1}")

        # UZS to USD
        rate2, created = ExchangeRate.objects.get_or_create(
            from_currency=uzs,
            to_currency=usd,
            defaults={"rate": uzs_to_usd_rate, "is_active": True},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created exchange rate: {rate2}"))
        else:
            # Update existing rate
            if rate2.rate != uzs_to_usd_rate:
                rate2.rate = uzs_to_usd_rate
                rate2.save()
                self.stdout.write(self.style.SUCCESS(f"Updated exchange rate: {rate2}"))
            else:
                self.stdout.write(f"Exchange rate already exists: {rate2}")

        self.stdout.write(self.style.SUCCESS("\nSetup complete!"))
        self.stdout.write(f"Default currency: {Currency.objects.get(is_default=True).code}")
        self.stdout.write(f"Active currencies: {Currency.objects.filter(is_active=True).count()}")
        self.stdout.write(f"Active exchange rates: {ExchangeRate.objects.filter(is_active=True).count()}")
