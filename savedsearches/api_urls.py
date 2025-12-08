from django.urls import path

from .views import SavedSearchDetailView, SavedSearchListCreateView, SavedSearchMarkViewedView, SavedSearchRunNowView

urlpatterns = [
    path("saved-searches", SavedSearchListCreateView.as_view(), name="saved-searches"),
    path("saved-searches/<int:pk>", SavedSearchDetailView.as_view(), name="saved-search"),
    path("saved-searches/<int:pk>/mark-viewed", SavedSearchMarkViewedView.as_view(), name="saved-search-mark-viewed"),
    path("saved-searches/<int:pk>/run", SavedSearchRunNowView.as_view(), name="saved-search-run"),
]

