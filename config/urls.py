from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.views.static import serve as serve_media
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.i18n import set_language

from listings.views import ListingOgPreviewView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Public share/unfurl page: serves OpenGraph tags to crawlers (Telegram,
    # etc.) and redirects real visitors to the SPA listing screen.
    path("l/<int:pk>", ListingOgPreviewView.as_view(), name="listing-og-preview"),
    path("i18n/setlang/", set_language, name="set_language"),
    path("healthz/", include("health.urls")),
    path("api/v1/", include("health.api_urls")),
    path("api/v1/", include("taxonomy.api_urls")),
    path("api/v1/", include("accounts.api_urls")),
    path("api/v1/", include("listings.api_urls")),
    path("api/v1/", include("searchapp.api_urls")),
    path("api/v1/", include("savedsearches.api_urls")),
    path("api/v1/", include("favorites.api_urls")),
    # path("api/v1/", include("uploads.api_urls")),
    path("api/v1/", include("moderation.api_urls")),
    path("api/v1/", include("chat.api_urls")),
    path("api/v1/", include("currency.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Serve uploaded media in both dev and production. Django's static() helper is
# dev-only (returns nothing when DEBUG is False), so use an explicit serve route.
urlpatterns += [
    re_path(
        rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$",
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
