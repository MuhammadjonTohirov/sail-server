from __future__ import annotations

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Listing
from ..serializers import ListingCreateSerializer, ListingSerializer
from ..utils import get_user_profile, sync_listing_contact_phone_mask
from taxonomy.models import Category, Location


class ListingCreateRawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["listings"],
        summary="Create a listing (raw)",
        description="Create a new listing by passing raw JSON fields directly, "
        "bypassing the serializer validation. Useful for simple clients.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "integer"},
                    "location": {"type": "integer"},
                    "description": {"type": "string"},
                    "price_amount": {"type": "number"},
                    "price_currency": {"type": "string"},
                    "condition": {"type": "string"},
                    "deal_type": {"type": "string"},
                    "contact_name": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "contact_phone": {"type": "string"},
                    "attributes": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["title", "category", "location"],
            }
        },
        responses={201: ListingSerializer},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"id": 1, "title": "iPhone 15", "status": "draft"},
                    "error": None,
                    "code": 201,
                },
                response_only=True,
            ),
        ],
    )
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
        contact_name = data.get("contact_name", "")
        contact_email = data.get("contact_email", "")
        contact_phone = data.get("contact_phone", "")

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
        profile = get_user_profile(request.user)

        if not contact_name and profile and profile.display_name:
            contact_name = profile.display_name
        if not contact_email and profile and profile.email:
            contact_email = profile.email
        if not contact_phone and profile and profile.phone_e164:
            contact_phone = profile.phone_e164

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
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

        sync_listing_contact_phone_mask(listing)
        listing.save(update_fields=["contact_phone_masked"])

        # Save attributes using existing logic for consistency
        if isinstance(attributes, list) and attributes:
            helper = ListingCreateSerializer(context={"request": request})
            helper._save_attributes(listing, attributes)

        # Respond with full listing payload
        output = ListingSerializer(listing, context={"request": request}).data
        return Response(output, status=201)
