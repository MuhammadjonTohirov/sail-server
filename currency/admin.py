from django.contrib import admin

from .models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "symbol", "is_active", "is_default", "updated_at"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["from_currency", "to_currency", "rate", "is_active", "updated_at"]
    list_filter = ["is_active", "from_currency", "to_currency"]
    search_fields = ["from_currency__code", "to_currency__code"]
    ordering = ["from_currency__code", "to_currency__code"]

    def get_readonly_fields(self, request, obj=None):
        # Make currencies readonly after creation
        if obj:
            return ["from_currency", "to_currency"]
        return []
