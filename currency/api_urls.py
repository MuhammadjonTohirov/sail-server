from django.urls import path, include

urlpatterns = [
    path("currency/", include("currency.urls")),
]
