from django.contrib import admin

from .models import Listing, ListingAttributeValue, ListingMedia


class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "category", "location", "price_amount", "status", "refreshed_at")
    list_filter = ("status", "category", "location")
    search_fields = ("title", "description")
    autocomplete_fields = ("user", "category", "location")
    inlines = [ListingMediaInline]


@admin.register(ListingAttributeValue)
class ListingAttributeAdmin(admin.ModelAdmin):
    list_display = ("listing", "attribute", "value_text", "value_number", "value_bool", "value_option_key")
    search_fields = ("value_text",)
    autocomplete_fields = ("listing", "attribute")


@admin.register(ListingMedia)
class ListingMediaAdmin(admin.ModelAdmin):
    list_display = ("listing", "type", "order", "uploaded_at")
    autocomplete_fields = ("listing",)

