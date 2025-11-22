from __future__ import annotations

from django.utils import timezone
from rest_framework import generics, mixins, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingMedia
from taxonomy.models import Category, Location
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    ListingCreateSerializer,
    ListingMediaSerializer,
    ListingSerializer,
    ListingUpdateSerializer,
)


class ListingCreateView(generics.CreateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ListingDetailView(generics.RetrieveAPIView):
    queryset = Listing.objects.select_related("category", "location", "user").prefetch_related("media")
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]


class ListingUpdateView(generics.UpdateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class MyListingsView(generics.ListAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Listing.objects.filter(user=self.request.user).prefetch_related("media")


class UserListingsView(generics.ListAPIView):
    """Get all active listings for a specific user (public view)"""
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        queryset = Listing.objects.filter(
            user_id=user_id,
            status=Listing.Status.ACTIVE
        ).select_related("category", "location", "user").prefetch_related("media")

        # Apply filters
        category_slug = self.request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        sort = self.request.query_params.get("sort", "newest")
        if sort == "newest":
            queryset = queryset.order_by("-refreshed_at", "-created_at")
        elif sort == "oldest":
            queryset = queryset.order_by("refreshed_at", "created_at")
        elif sort == "price_asc":
            queryset = queryset.order_by("price_amount")
        elif sort == "price_desc":
            queryset = queryset.order_by("-price_amount")

        return queryset


class ListingRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        listing.refreshed_at = timezone.now()
        listing.save(update_fields=["refreshed_at"])
        return Response({"status": "refreshed", "refreshed_at": listing.refreshed_at})


class ListingMediaUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded"}, status=400)

        media = ListingMedia(listing=listing, image=file_obj)
        media.save()
        serializer = ListingMediaSerializer(media, context={"request": request})
        return Response(serializer.data, status=201)


class ListingMediaDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int, media_id: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
            media = ListingMedia.objects.get(id=media_id, listing=listing)
        except (Listing.DoesNotExist, ListingMedia.DoesNotExist):
            return Response({"detail": "Not found"}, status=404)

        media.delete()
        return Response({"status": "deleted"}, status=200)


class ListingMediaReorderView(APIView):
    """Reorder media for a listing. Expects: {"media_ids": [3, 1, 2]}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        media_ids = request.data.get("media_ids", [])
        if not isinstance(media_ids, list):
            return Response({"detail": "media_ids must be a list"}, status=400)

        # Verify all media belong to this listing
        existing_media = list(listing.media.all())
        existing_ids = {m.id for m in existing_media}

        for media_id in media_ids:
            if media_id not in existing_ids:
                return Response(
                    {"detail": f"Media {media_id} does not belong to listing {pk}"},
                    status=400
                )

        # Update order field for each media
        for order, media_id in enumerate(media_ids):
            ListingMedia.objects.filter(id=media_id, listing=listing).update(order=order)

        # Return updated media list
        updated_media = listing.media.all().order_by("order", "id")
        serializer = ListingMediaSerializer(updated_media, many=True, context={"request": request})
        return Response({"media": serializer.data}, status=200)


class ListingCreateRawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data or {}

        # Required fields
        title = data.get("title")
        category_id = data.get("category")
        location_id = data.get("location")
        if not title or not category_id or not location_id:
            return Response({
                "detail": "'title', 'category', and 'location' are required."
            }, status=400)

        # Validate category/location exist
        try:
            category_id = int(category_id)
        except Exception:
            return Response({"category": "Must be an integer id."}, status=400)
        try:
            location_id = int(location_id)
        except Exception:
            return Response({"location": "Must be an integer id."}, status=400)

        if not Category.objects.filter(pk=category_id).exists():
            return Response({"category": "Not found."}, status=400)
        if not Location.objects.filter(pk=location_id).exists():
            return Response({"location": "Not found."}, status=400)

        # Optional fields and coercion
        description = data.get("description", "")
        price_amount = data.get("price_amount", 0)
        price_currency = data.get("price_currency", "UZS")
        is_price_negotiable = data.get("is_price_negotiable", False)
        condition = data.get("condition", Listing.Condition.USED)
        deal_type = data.get("deal_type", Listing.DealType.SELL)
        seller_type = data.get("seller_type", Listing.SellerType.PERSON)
        lat = data.get("lat")
        lon = data.get("lon")
        attributes = data.get("attributes", [])

        # Coerce booleans/numbers/enums
        def to_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.strip().lower() in {"1", "true", "yes", "on"}
            return False

        def to_float_or_none(v):
            if v is None or v == "":
                return None
            try:
                return float(v)
            except Exception:
                return None

        try:
            price_amount = float(price_amount)
        except Exception:
            return Response({"price_amount": "Must be a number."}, status=400)

        is_price_negotiable = to_bool(is_price_negotiable)
        lat = to_float_or_none(lat)
        lon = to_float_or_none(lon)

        if condition not in dict(Listing.Condition.choices):
            return Response({"condition": f"Invalid. Allowed: {list(dict(Listing.Condition.choices).keys())}"}, status=400)
        if deal_type not in dict(Listing.DealType.choices):
            return Response({"deal_type": f"Invalid. Allowed: {list(dict(Listing.DealType.choices).keys())}"}, status=400)
        if seller_type not in dict(Listing.SellerType.choices):
            return Response({"seller_type": f"Invalid. Allowed: {list(dict(Listing.SellerType.choices).keys())}"}, status=400)

        # Create listing
        listing = Listing.objects.create(
            user=request.user,
            title=title,
            description=description,
            price_amount=price_amount,
            price_currency=price_currency,
            is_price_negotiable=is_price_negotiable,
            condition=condition,
            deal_type=deal_type,
            seller_type=seller_type,
            category_id=category_id,
            location_id=location_id,
            lat=lat,
            lon=lon,
        )

        # Phone mask (same logic as serializer.create)
        user = request.user
        if hasattr(user, "profile") and getattr(user.profile, "phone_e164", None):
            phone = user.profile.phone_e164
        else:
            phone = user.username
        listing.contact_phone_masked = phone#(phone[:4] + "****" + phone[-2:]) if phone else ""
        listing.save(update_fields=["contact_phone_masked"])

        # Save attributes using existing logic for consistency
        if isinstance(attributes, list) and attributes:
            from .serializers import ListingCreateSerializer, ListingSerializer
            helper = ListingCreateSerializer(context={"request": request})
            helper._save_attributes(listing, attributes)

        # Respond with full listing payload
        from .serializers import ListingSerializer as OutSerializer
        output = OutSerializer(listing, context={"request": request}).data
        return Response(output, status=201)


class ListingUpdateRawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk: int):
        data = request.data or {}

        # Get the listing and verify ownership
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        # Extract and validate fields
        title = data.get("title")
        category_id = data.get("category")
        location_id = data.get("location")
        contact_phone = data.get("contact_phone")
        contact_name = data.get("contact_name")
        contact_email = data.get("contact_email")
        # Validate required fields if provided
        if title is not None and not title:
            return Response({"title": "Title cannot be empty."}, status=400)

        # Validate category if provided
        if category_id is not None:
            try:
                category_id = int(category_id)
            except Exception:
                return Response({"category": "Must be an integer id."}, status=400)
            if not Category.objects.filter(pk=category_id).exists():
                return Response({"category": "Not found."}, status=400)

        # Validate location if provided
        if location_id is not None:
            try:
                location_id = int(location_id)
            except Exception:
                return Response({"location": "Must be an integer id."}, status=400)
            if not Location.objects.filter(pk=location_id).exists():
                return Response({"location": "Not found."}, status=400)

        # Helper functions
        def to_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.strip().lower() in {"1", "true", "yes", "on"}
            return False

        def to_float_or_none(v):
            if v is None or v == "":
                return None
            try:
                return float(v)
            except Exception:
                return None

        # Update basic fields
        if title is not None:
            listing.title = title
        if "description" in data:
            listing.description = data.get("description", "")
        if "price_amount" in data:
            try:
                listing.price_amount = float(data.get("price_amount", 0))
            except Exception:
                return Response({"price_amount": "Must be a number."}, status=400)
        if "price_currency" in data:
            listing.price_currency = data.get("price_currency", "UZS")
        if "is_price_negotiable" in data:
            listing.is_price_negotiable = to_bool(data.get("is_price_negotiable"))
        if "condition" in data:
            condition = data.get("condition")
            if condition not in dict(Listing.Condition.choices):
                return Response({"condition": f"Invalid. Allowed: {list(dict(Listing.Condition.choices).keys())}"}, status=400)
            listing.condition = condition
        if "deal_type" in data:
            deal_type = data.get("deal_type")
            if deal_type not in dict(Listing.DealType.choices):
                return Response({"deal_type": f"Invalid. Allowed: {list(dict(Listing.DealType.choices).keys())}"}, status=400)
            listing.deal_type = deal_type
        if "seller_type" in data:
            seller_type = data.get("seller_type")
            if seller_type not in dict(Listing.SellerType.choices):
                return Response({"seller_type": f"Invalid. Allowed: {list(dict(Listing.SellerType.choices).keys())}"}, status=400)
            listing.seller_type = seller_type
        if category_id is not None:
            listing.category_id = category_id
        if location_id is not None:
            listing.location_id = location_id
        if "lat" in data:
            listing.lat = to_float_or_none(data.get("lat"))
        if "lon" in data:
            listing.lon = to_float_or_none(data.get("lon"))

        listing.contact_email = contact_email if contact_email is not None else listing.contact_email
        listing.contact_name = contact_name if contact_name is not None else listing.contact_name
        listing.contact_phone = contact_phone if contact_phone is not None else listing.contact_phone

        listing.save()

        # Handle attributes if provided
        attributes = data.get("attributes")
        if isinstance(attributes, list):
            from .serializers import ListingCreateSerializer
            helper = ListingCreateSerializer(context={"request": request})
            helper._save_attributes(listing, attributes)

        # Respond with full listing payload
        from .serializers import ListingSerializer as OutSerializer
        output = OutSerializer(listing, context={"request": request}).data
        return Response(output, status=200)


class ListingDeactivateView(APIView):
    """Deactivate a listing by setting its status to paused"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        listing.status = Listing.Status.PAUSED
        listing.save(update_fields=["status"])
        return Response({"status": "deactivated", "new_status": listing.status})


class ListingActivateView(APIView):
    """Activate a paused listing by setting its status back to active"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        if listing.status not in [Listing.Status.PAUSED, Listing.Status.CLOSED]:
            return Response(
                {"detail": "Can only activate paused or closed listings"},
                status=400
            )

        listing.status = Listing.Status.ACTIVE
        listing.refreshed_at = timezone.now()
        listing.save(update_fields=["status", "refreshed_at"])
        return Response({"status": "activated", "new_status": listing.status})


class ListingDeleteView(APIView):
    """Delete a listing permanently"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int):
        try:
            listing = Listing.objects.get(pk=pk, user=request.user)
        except Listing.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        listing.delete()
        return Response({"status": "deleted"}, status=200)
