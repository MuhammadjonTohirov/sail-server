from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.text import Truncator
from django.utils.translation import get_language
from django.views import View

from ..models import Listing, ListingMedia


class ListingOgPreviewView(View):
    """Server-rendered listing page carrying OpenGraph/Twitter Card meta tags.

    Link unfurlers (Telegram, WhatsApp, Facebook, X) read these tags to render a
    rich preview card. The SPA at ``WEB_BASE_URL`` is client-rendered and exposes
    nothing to crawlers, so the canonical share URL points here instead. Real
    browsers that open this page are redirected straight to the SPA listing
    screen, while crawlers keep the meta tags.
    """

    def get(self, request, pk: int) -> HttpResponse:
        try:
            listing = (
                Listing.objects.select_related("category", "location")
                .get(pk=pk, status=Listing.Status.ACTIVE)
            )
        except Listing.DoesNotExist as exc:
            raise Http404("Listing not found") from exc

        web_base = settings.WEB_BASE_URL.rstrip("/")
        listing_url = f"{web_base}/l/{listing.id}"

        photo = (
            listing.media.filter(type=ListingMedia.Type.PHOTO)
            .order_by("order", "id")
            .first()
        )
        # Crawlers cannot resolve relative paths, so the image must be absolute.
        image_url = (
            request.build_absolute_uri(photo.image.url)
            if photo and photo.image
            else ""
        )
        has_price = bool(listing.price_amount and listing.price_amount > 0)

        context = {
            "lang": get_language() or "ru",
            "canonical_url": listing_url,
            "redirect_url": listing_url,
            "site_name": urlparse(web_base).netloc or "sail.uz",
            "og_title": self._build_title(listing),
            "og_description": self._build_description(listing),
            "image_url": image_url,
            "image_width": photo.width if photo else None,
            "image_height": photo.height if photo else None,
            "price_amount": listing.price_amount if has_price else None,
            "price_currency": listing.price_currency,
        }
        response = render(request, "listings/og_preview.html", context)
        # Let Telegram/CDNs cache the unfurl briefly without serving stale cards.
        response["Cache-Control"] = "public, max-age=300"
        return response

    @staticmethod
    def _build_title(listing: Listing) -> str:
        category = listing.category.name if listing.category_id else ""
        location = listing.location.name if listing.location_id else ""
        place = ", ".join(part for part in (category, location) if part)
        tail = " - ".join(part for part in (listing.price_display, place) if part)
        return f"{listing.title}: {tail}" if tail else listing.title

    @staticmethod
    def _build_description(listing: Listing) -> str:
        text = " ".join((listing.description or "").split())
        if text:
            return Truncator(text).chars(200, truncate="…")
        # Fall back to structured info when there is no free-text description.
        category = listing.category.name if listing.category_id else ""
        location = listing.location.name if listing.location_id else ""
        return " · ".join(
            part for part in (listing.price_display, category, location) if part
        )
