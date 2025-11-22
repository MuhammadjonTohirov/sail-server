from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing
from .models import FavoriteListing, RecentlyViewedListing
from .serializers import FavoriteListingSerializer, RecentlyViewedListingSerializer


class FavoriteListingListView(generics.ListAPIView):
    """
    GET /api/v1/favorites
    List all favorite listings for the authenticated user.
    """
    serializer_class = FavoriteListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteListing.objects.filter(
            user=self.request.user
        ).select_related("listing", "listing__location").prefetch_related("listing__media")


class FavoriteListingToggleView(APIView):
    """
    POST /api/v1/favorites/<listing_id>/toggle
    Add or remove a listing from favorites.
    Returns: {"favorited": true/false}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, listing_id: int):
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        favorite, created = FavoriteListing.objects.get_or_create(
            user=request.user,
            listing=listing
        )

        if not created:
            # Already favorited, so remove it
            favorite.delete()
            return Response({"favorited": False})

        return Response({"favorited": True}, status=status.HTTP_201_CREATED)


class FavoriteListingDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/v1/favorites/<listing_id>
    Remove a listing from favorites.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "listing_id"
    lookup_url_kwarg = "listing_id"

    def get_queryset(self):
        return FavoriteListing.objects.filter(user=self.request.user)

    def get_object(self):
        listing_id = self.kwargs.get("listing_id")
        try:
            return self.get_queryset().get(listing_id=listing_id)
        except FavoriteListing.DoesNotExist:
            return None

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecentlyViewedListingListView(generics.ListAPIView):
    """
    GET /api/v1/recently-viewed
    List recently viewed listings for the authenticated user or session.
    """
    serializer_class = RecentlyViewedListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return RecentlyViewedListing.objects.filter(
                user=self.request.user
            ).select_related("listing", "listing__location").prefetch_related("listing__media")[:50]

        # For anonymous users, use session
        session_key = self.request.session.session_key
        if not session_key:
            return RecentlyViewedListing.objects.none()

        return RecentlyViewedListing.objects.filter(
            session_key=session_key
        ).select_related("listing", "listing__location").prefetch_related("listing__media")[:50]


class RecentlyViewedListingTrackView(APIView):
    """
    POST /api/v1/recently-viewed/<listing_id>
    Track that a user viewed a listing.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, listing_id: int):
        import time
        from django.db import OperationalError

        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Retry logic for database locks (SQLite)
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms

        for attempt in range(max_retries):
            try:
                if request.user.is_authenticated:
                    # For authenticated users
                    obj, created = RecentlyViewedListing.objects.update_or_create(
                        user=request.user,
                        listing=listing,
                        defaults={"session_key": None}
                    )
                else:
                    # For anonymous users, use session
                    if not request.session.session_key:
                        request.session.create()

                    obj, created = RecentlyViewedListing.objects.update_or_create(
                        session_key=request.session.session_key,
                        listing=listing,
                        defaults={"user": None}
                    )

                return Response(
                    {"tracked": True},
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )

            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    # Wait and retry with exponential backoff
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Double the delay for next attempt
                else:
                    # Last attempt or different error - raise it
                    raise


class RecentlyViewedListingClearView(APIView):
    """
    DELETE /api/v1/recently-viewed
    Clear all recently viewed listings for the user or session.
    """
    permission_classes = [permissions.AllowAny]

    def delete(self, request):
        if request.user.is_authenticated:
            count, _ = RecentlyViewedListing.objects.filter(user=request.user).delete()
        else:
            session_key = request.session.session_key
            if session_key:
                count, _ = RecentlyViewedListing.objects.filter(session_key=session_key).delete()
            else:
                count = 0

        return Response({"deleted": count}, status=status.HTTP_200_OK)
