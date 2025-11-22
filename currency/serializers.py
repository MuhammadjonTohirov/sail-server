from rest_framework import serializers

from .models import Currency, ExchangeRate


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["code", "name", "symbol", "is_default"]


class ExchangeRateSerializer(serializers.ModelSerializer):
    from_currency = serializers.CharField(source="from_currency.code")
    to_currency = serializers.CharField(source="to_currency.code")

    class Meta:
        model = ExchangeRate
        fields = ["from_currency", "to_currency", "rate"]
