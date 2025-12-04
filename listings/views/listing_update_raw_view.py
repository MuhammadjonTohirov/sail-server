from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing
from ..serializers import ListingCreateSerializer, ListingSerializer
from taxonomy.models import Category, Location


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
            helper = ListingCreateSerializer(context={"request": request})
            helper._save_attributes(listing, attributes)

        # Respond with full listing payload
        output = ListingSerializer(listing, context={"request": request}).data
        return Response(output, status=200)
