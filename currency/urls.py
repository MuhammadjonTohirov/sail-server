from django.urls import path

from .views import CurrencyConfigView, CurrencyConvertView

urlpatterns = [
    path("config", CurrencyConfigView.as_view(), name="currency-config"),
    path("convert", CurrencyConvertView.as_view(), name="currency-convert"),
]
