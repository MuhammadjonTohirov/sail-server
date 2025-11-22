from django.urls import path
from .views import ApiHealthView, I18nView

urlpatterns = [
    path("health", ApiHealthView.as_view(), name="api-health"),
    path("i18n", I18nView.as_view(), name="i18n"),
]
