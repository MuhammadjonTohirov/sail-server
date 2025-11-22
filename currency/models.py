from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator


class Currency(models.Model):
    """Currency model for multi-currency support"""

    code = models.CharField(max_length=3, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Ensure only one default currency
        if self.is_default:
            Currency.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """Exchange rate between two currencies"""

    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="rates_from"
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="rates_to"
    )
    rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))]
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        unique_together = [["from_currency", "to_currency"]]
        ordering = ["from_currency__code", "to_currency__code"]

    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code}"

    def save(self, *args, **kwargs):
        # Prevent same currency exchange rate
        if self.from_currency_id == self.to_currency_id:
            raise ValueError("Cannot create exchange rate for same currency")
        super().save(*args, **kwargs)
