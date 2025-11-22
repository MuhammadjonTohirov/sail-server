from django.urls import path

from .views import (
    ListingActivateView,
    ListingCreateView,
    ListingCreateRawView,
    ListingDeactivateView,
    ListingDeleteView,
    ListingDetailView,
    ListingMediaDeleteView,
    ListingMediaReorderView,
    ListingMediaUploadView,
    ListingRefreshView,
    ListingUpdateView,
    ListingUpdateRawView,
    MyListingsView,
    UserListingsView,
)

urlpatterns = [
    path("listings", ListingCreateView.as_view(), name="listing-create"),
    path("listings/raw", ListingCreateRawView.as_view(), name="listing-create-raw"),
    path("listings/<int:pk>", ListingDetailView.as_view(), name="listing-detail"),
    path("listings/<int:pk>/edit", ListingUpdateView.as_view(), name="listing-update"),
    path("listings/<int:pk>/edit/raw", ListingUpdateRawView.as_view(), name="listing-update-raw"),
    path("listings/<int:pk>/refresh", ListingRefreshView.as_view(), name="listing-refresh"),
    path("listings/<int:pk>/deactivate", ListingDeactivateView.as_view(), name="listing-deactivate"),
    path("listings/<int:pk>/activate", ListingActivateView.as_view(), name="listing-activate"),
    path("listings/<int:pk>/delete", ListingDeleteView.as_view(), name="listing-delete"),
    path("listings/<int:pk>/media", ListingMediaUploadView.as_view(), name="listing-media-upload"),
    path("listings/<int:pk>/media/<int:media_id>", ListingMediaDeleteView.as_view(), name="listing-media-delete"),
    path("listings/<int:pk>/media/reorder", ListingMediaReorderView.as_view(), name="listing-media-reorder"),
    path("my/listings", MyListingsView.as_view(), name="my-listings"),
    path("users/<int:user_id>/listings", UserListingsView.as_view(), name="user-listings"),
]
