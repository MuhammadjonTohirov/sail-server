from django.contrib import admin

from .models import FavoriteListing, RecentlyViewedListing


@admin.register(FavoriteListing)
class FavoriteListingAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "listing", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "user__phone", "listing__title"]
    raw_id_fields = ["user", "listing"]
    date_hierarchy = "created_at"


@admin.register(RecentlyViewedListing)
class RecentlyViewedListingAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_key", "listing", "viewed_at"]
    list_filter = ["viewed_at"]
    search_fields = ["user__username", "user__phone", "session_key", "listing__title"]
    raw_id_fields = ["user", "listing"]
    date_hierarchy = "viewed_at"
