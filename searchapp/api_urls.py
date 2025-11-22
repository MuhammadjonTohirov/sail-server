from django.urls import path

from .views import ListingSearchView

urlpatterns = [
    path("search/listings", ListingSearchView.as_view(), name="search-listings"),
]

