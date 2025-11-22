from django.urls import path

from .views import CategoriesTreeView, CategoryAttributesView, LocationsView

urlpatterns = [
    path("categories", CategoriesTreeView.as_view(), name="categories-tree"),
    path("categories/<int:pk>/attributes", CategoryAttributesView.as_view(), name="category-attributes"),
    path("locations", LocationsView.as_view(), name="locations"),
]

