from django.contrib import admin

from .models import Attribute, Category, Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "parent")
    list_filter = ("kind",)
    search_fields = ("name", "slug")
    autocomplete_fields = ("parent",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent", "icon", "is_leaf", "order")
    list_filter = ("level", "is_leaf")
    search_fields = ("name", "slug", "icon")
    autocomplete_fields = ("parent",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("category", "key", "type", "is_indexed")
    list_filter = ("type", "is_indexed")
    search_fields = ("key", "label")
    autocomplete_fields = ("category",)
