from decimal import Decimal
from typing import Optional

from django.core.cache import cache

from .models import Currency, ExchangeRate


class CurrencyService:
    """Service for currency conversion and exchange rate management"""

    CACHE_TIMEOUT = 3600  # 1 hour

    @staticmethod
    def get_active_currencies():
        """Get all active currencies"""
        cache_key = "currency:active_currencies"
        currencies = cache.get(cache_key)

        if currencies is None:
            currencies = list(
                Currency.objects.filter(is_active=True).values(
                    "code", "name", "symbol", "is_default"
                )
            )
            cache.set(cache_key, currencies, CurrencyService.CACHE_TIMEOUT)

        return currencies

    @staticmethod
    def get_default_currency() -> Optional[Currency]:
        """Get the default currency"""
        cache_key = "currency:default"
        default = cache.get(cache_key)

        if default is None:
            try:
                default = Currency.objects.get(is_default=True)
                cache.set(cache_key, default, CurrencyService.CACHE_TIMEOUT)
            except Currency.DoesNotExist:
                # Fallback to UZS if no default set
                default = Currency.objects.filter(code="UZS").first()
                if default:
                    cache.set(cache_key, default, CurrencyService.CACHE_TIMEOUT)

        return default

    @staticmethod
    def get_exchange_rates():
        """Get all active exchange rates as a nested dictionary"""
        cache_key = "currency:exchange_rates"
        rates = cache.get(cache_key)

        if rates is None:
            rates = {}
            for er in ExchangeRate.objects.filter(is_active=True).select_related(
                "from_currency", "to_currency"
            ):
                from_code = er.from_currency.code
                to_code = er.to_currency.code

                if from_code not in rates:
                    rates[from_code] = {}

                rates[from_code][to_code] = float(er.rate)

            # Add identity rates (USD -> USD = 1.0)
            for currency in Currency.objects.filter(is_active=True):
                code = currency.code
                if code not in rates:
                    rates[code] = {}
                rates[code][code] = 1.0

            cache.set(cache_key, rates, CurrencyService.CACHE_TIMEOUT)

        return rates

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return Decimal("1.0")

        cache_key = f"currency:rate:{from_currency}:{to_currency}"
        rate = cache.get(cache_key)

        if rate is None:
            try:
                from_curr = Currency.objects.get(code=from_currency, is_active=True)
                to_curr = Currency.objects.get(code=to_currency, is_active=True)

                exchange_rate = ExchangeRate.objects.get(
                    from_currency=from_curr, to_currency=to_curr, is_active=True
                )
                rate = exchange_rate.rate
                cache.set(cache_key, rate, CurrencyService.CACHE_TIMEOUT)
            except (Currency.DoesNotExist, ExchangeRate.DoesNotExist):
                return None

        return rate

    @staticmethod
    def convert_price(
        amount: Decimal, from_currency: str, to_currency: str
    ) -> Optional[Decimal]:
        """Convert price from one currency to another"""
        if amount is None:
            return None

        rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            return None

        # Ensure both are Decimal for proper multiplication
        from decimal import Decimal as D
        if not isinstance(amount, D):
            amount = D(str(amount))
        if not isinstance(rate, D):
            rate = D(str(rate))

        return amount * rate

    @staticmethod
    def normalize_price_to_base(amount: Decimal, currency: str) -> Decimal:
        """
        Normalize price to base currency (UZS) for consistent sorting.
        Returns the amount in UZS regardless of original currency.
        """
        if amount is None or amount == 0:
            return Decimal("0")

        default_currency = CurrencyService.get_default_currency()
        if not default_currency:
            return amount

        base_currency_code = default_currency.code

        if currency == base_currency_code:
            return amount

        converted = CurrencyService.convert_price(amount, currency, base_currency_code)
        return converted if converted is not None else amount

    @staticmethod
    def clear_cache():
        """Clear all currency-related cache"""
        cache.delete("currency:active_currencies")
        cache.delete("currency:default")
        cache.delete("currency:exchange_rates")
        # Also clear individual exchange rate caches if needed
        for from_curr in Currency.objects.filter(is_active=True):
            for to_curr in Currency.objects.filter(is_active=True):
                cache.delete(f"currency:rate:{from_curr.code}:{to_curr.code}")
