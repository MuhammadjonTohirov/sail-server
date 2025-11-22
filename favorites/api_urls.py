from django.urls import path

from .views import (
    FavoriteListingListView,
    FavoriteListingToggleView,
    FavoriteListingDeleteView,
    RecentlyViewedListingListView,
    RecentlyViewedListingTrackView,
    RecentlyViewedListingClearView,
)

urlpatterns = [
    # Favorites
    path("favorites", FavoriteListingListView.as_view(), name="favorites-list"),
    path("favorites/<int:listing_id>/toggle", FavoriteListingToggleView.as_view(), name="favorites-toggle"),
    path("favorites/<int:listing_id>", FavoriteListingDeleteView.as_view(), name="favorites-delete"),

    # Recently Viewed
    path("recently-viewed", RecentlyViewedListingListView.as_view(), name="recently-viewed-list"),
    path("recently-viewed/<int:listing_id>", RecentlyViewedListingTrackView.as_view(), name="recently-viewed-track"),
    path("recently-viewed/clear", RecentlyViewedListingClearView.as_view(), name="recently-viewed-clear"),
]
