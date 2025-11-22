from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.i18n import set_language

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/setlang/", set_language, name="set_language"),
    path("healthz/", include("health.urls")),
    path("api/v1/", include("health.api_urls")),
    path("api/v1/", include("taxonomy.api_urls")),
    path("api/v1/", include("accounts.api_urls")),
    path("api/v1/", include("listings.api_urls")),
    path("api/v1/", include("searchapp.api_urls")),
    path("api/v1/", include("savedsearches.api_urls")),
    path("api/v1/", include("favorites.api_urls")),
    path("api/v1/", include("uploads.api_urls")),
    path("api/v1/", include("moderation.api_urls")),
    path("api/v1/", include("chat.api_urls")),
    path("api/v1/", include("currency.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Serve uploaded media in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
