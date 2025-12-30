from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing
from ..models import ChatThread


class SyncChatAvailabilityView(APIView):
    """
    Sync listing availability status for user's chat threads.
    Called when user visits chat page to ensure listing statuses are up to date.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Get all threads where user is a participant
        threads = ChatThread.objects.filter(
            participants__user_id=user.id,
            participants__is_deleted=False
        ).distinct()

        # Get unique listing IDs
        listing_ids = list(threads.values_list('listing_id', flat=True).distinct())

        if not listing_ids:
            return Response({"synced": 0, "updated": 0})

        # Fetch current listing statuses
        listings = Listing.objects.filter(id__in=listing_ids).values('id', 'status')
        listing_status_map = {l['id']: l['status'] for l in listings}

        updated_count = 0
        now = timezone.now()

        for thread in threads:
            listing_status = listing_status_map.get(thread.listing_id)

            if listing_status is None:
                # Listing was deleted
                new_availability = ChatThread.ListingAvailability.DELETED
            elif listing_status == Listing.Status.ACTIVE:
                new_availability = ChatThread.ListingAvailability.AVAILABLE
            else:
                # Listing exists but is not active (paused, closed, expired, etc.)
                new_availability = ChatThread.ListingAvailability.UNAVAILABLE

            if thread.listing_availability != new_availability:
                thread.listing_availability = new_availability
                thread.listing_availability_checked_at = now
                thread.save(update_fields=['listing_availability', 'listing_availability_checked_at', 'updated_at'])
                updated_count += 1
            elif thread.listing_availability_checked_at is None:
                # Update check timestamp even if status unchanged
                thread.listing_availability_checked_at = now
                thread.save(update_fields=['listing_availability_checked_at', 'updated_at'])

        return Response({
            "synced": len(listing_ids),
            "updated": updated_count
        })


class BulkListingStatusView(APIView):
    """
    Get availability status for multiple listings at once.
    Used for checking listing availability in chat threads.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        listing_ids = request.data.get('listing_ids', [])

        if not listing_ids:
            return Response({"statuses": {}})

        if not isinstance(listing_ids, list):
            return Response(
                {"error": "listing_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Limit to prevent abuse
        if len(listing_ids) > 100:
            return Response(
                {"error": "Maximum 100 listing IDs allowed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            listing_ids = [int(lid) for lid in listing_ids]
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid listing ID format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        listings = Listing.objects.filter(id__in=listing_ids).values('id', 'status')

        statuses = {}
        for listing in listings:
            if listing['status'] == Listing.Status.ACTIVE:
                statuses[listing['id']] = 'available'
            else:
                statuses[listing['id']] = 'unavailable'

        # Mark missing listings as deleted
        for lid in listing_ids:
            if lid not in statuses:
                statuses[lid] = 'deleted'

        return Response({"statuses": statuses})
