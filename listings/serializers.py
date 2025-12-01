from __future__ import annotations

from typing import Any, Dict, List

from rest_framework import serializers
from django.conf import settings

from taxonomy.models import Attribute

from .models import Listing, ListingAttributeValue, ListingMedia


class ListingMediaSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ["id", "type", "image", "image_url", "width", "height", "order", "uploaded_at"]
        read_only_fields = ["id", "image_url", "uploaded_at"]

    def get_image_url(self, obj):  # pragma: no cover
        request = self.context.get("request")
        if request:
            return obj.image.url#request.build_absolute_uri(obj.image.url)
        return obj.image.url


class ListingSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)
    attributes = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    location_slug = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    price_normalized = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "price_amount",
            "price_currency",
            "is_price_negotiable",
            "condition",
            "deal_type",
            "seller_type",
            "status",
            "category",
            "category_name",
            "category_slug",
            "location",
            "location_name",
            "location_slug",
            "created_at",
            "refreshed_at",
            "expires_at",
            "quality_score",
            "contact_phone_masked",
            "contact_name",
            "contact_email",
            "contact_phone",
            "lat",
            "lon",
            "media",
            "attributes",
            "seller",
            "price_normalized",
        ]
        read_only_fields = [
            "status",
            "created_at",
            "refreshed_at",
            "expires_at",
            "quality_score",
            "contact_phone_masked",
            "price_normalized",
        ]

    def get_attributes(self, obj: Listing) -> List[Dict[str, Any]]:  # pragma: no cover
        rows = (
            ListingAttributeValue.objects.filter(listing=obj)
            .select_related("attribute")
            .order_by("attribute_id", "id")
        )
        grouped: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            attr = row.attribute
            if attr.id not in grouped:
                grouped[attr.id] = {
                    "attribute": attr.id,
                    "key": attr.key,
                    "label": self._attr_label(attr),
                    "type": attr.type,
                    "value": None,
                }
            if attr.type == Attribute.Type.MULTISELECT:
                if grouped[attr.id]["value"] is None:
                    grouped[attr.id]["value"] = []
                grouped[attr.id]["value"].append(row.value_option_key)
            elif attr.type == Attribute.Type.SELECT:
                grouped[attr.id]["value"] = row.value_option_key
            elif attr.type == Attribute.Type.NUMBER or attr.type == Attribute.Type.RANGE:
                grouped[attr.id]["value"] = row.value_number
            elif attr.type == Attribute.Type.BOOLEAN:
                grouped[attr.id]["value"] = row.value_bool
            else:
                grouped[attr.id]["value"] = row.value_text
        return list(grouped.values())

    def _lang(self) -> str:
        req = self.context.get("request")
        if not req:
            return "ru"
        return req.query_params.get("lang") or "ru"

    def _attr_label(self, attr):  # pragma: no cover
        lang = self._lang()
        if lang == "uz":
            return getattr(attr, "label_uz", None) or attr.label or getattr(attr, "label_ru", None)
        return getattr(attr, "label_ru", None) or attr.label or getattr(attr, "label_uz", None)

    def get_category_name(self, obj: Listing) -> str:  # pragma: no cover
        cat = getattr(obj, "category", None)
        if not cat:
            return ""
        lang = self._lang()
        if lang == "uz":
            return getattr(cat, "name_uz", None) or cat.name or getattr(cat, "name_ru", None)
        return getattr(cat, "name_ru", None) or cat.name or getattr(cat, "name_uz", None)

    def get_category_slug(self, obj: Listing) -> str:  # pragma: no cover
        cat = getattr(obj, "category", None)
        return getattr(cat, "slug", "") if cat else ""

    def get_location_name(self, obj: Listing) -> str:  # pragma: no cover
        loc = getattr(obj, "location", None)
        if not loc:
            return ""
        lang = self._lang()
        if lang == "uz":
            return getattr(loc, "name_uz", None) or loc.name or getattr(loc, "name_ru", None)
        return getattr(loc, "name_ru", None) or loc.name or getattr(loc, "name_uz", None)

    def get_location_slug(self, obj: Listing) -> str:  # pragma: no cover
        loc = getattr(obj, "location", None)
        return getattr(loc, "slug", "") if loc else ""

    def get_seller(self, obj: Listing) -> Dict[str, Any]:  # pragma: no cover
        user = getattr(obj, "user", None)
        if not user:
            return {}
        profile = getattr(user, "profile", None)
        name = ""
        avatar_url = ""
        logo = ""
        banner = ""
        since = None
        last_active = None
        if profile:
            name = profile.display_name or profile.phone_e164
            avatar_url = profile.avatar_url or ""
            since = profile.created_at
            logo = profile.logo.url if profile.logo else ""
            banner = profile.banner.url if profile.banner else ""
            last_active = profile.last_active_at
        return {
            "id": user.id,
            "name": name,
            "avatar_url": avatar_url,
            "since": since,
            "logo": logo,
            "banner": banner,
            "last_active_at": last_active,
        }

    def get_price_normalized(self, obj: Listing) -> float:  # pragma: no cover
        """Return price normalized to base currency (UZS) for consistent sorting"""
        from currency.services import CurrencyService

        if obj.price_amount is None or obj.price_amount == 0:
            return 0.0

        normalized = CurrencyService.normalize_price_to_base(
            obj.price_amount, obj.price_currency
        )
        return float(normalized)


class ListingAttributeInputSerializer(serializers.Serializer):
    attribute = serializers.JSONField()  # accept id or key; validate handles coercion
    value = serializers.JSONField()

    def validate(self, data):
        attr_ref = data["attribute"]
        # Coerce attribute reference to Attribute by id or by key
        attrs_by_id = self.context.get("attrs_by_id", {})
        attrs_by_key = self.context.get("attrs_by_key", {})
        attr = None
        try:
            # numeric id
            attr_id = int(attr_ref)
            attr = attrs_by_id.get(attr_id)
        except Exception:
            # string key
            if isinstance(attr_ref, str):
                attr = attrs_by_key.get(attr_ref)
        if not attr:
            # In dev, be lenient and allow skipping unknown attributes
            if self.context.get("lenient"):
                data["_skip"] = True
                return data
            raise serializers.ValidationError({"attribute": "Unknown attribute for this category."})

        # rewrite to canonical id for downstream usage
        data["attribute"] = attr.id
        value = data["value"]

        typ = attr.type
        if typ == Attribute.Type.TEXT:
            if not isinstance(value, str):
                raise serializers.ValidationError({"value": "Expected string."})
        elif typ in (Attribute.Type.NUMBER, Attribute.Type.RANGE):
            if not isinstance(value, (int, float)):
                raise serializers.ValidationError({"value": "Expected number."})
            # Min/Max validation when configured
            if attr.min_number is not None and float(value) < float(attr.min_number):
                raise serializers.ValidationError({"value": f"Must be >= {attr.min_number}."})
            if attr.max_number is not None and float(value) > float(attr.max_number):
                raise serializers.ValidationError({"value": f"Must be <= {attr.max_number}."})
        elif typ == Attribute.Type.BOOLEAN:
            if not isinstance(value, bool):
                raise serializers.ValidationError({"value": "Expected boolean."})
        elif typ == Attribute.Type.SELECT:
            if not isinstance(value, (str, int)):
                raise serializers.ValidationError({"value": "Expected scalar option key."})
            if attr.options and str(value) not in [str(o) for o in attr.options]:
                raise serializers.ValidationError({"value": "Option not allowed."})
        elif typ == Attribute.Type.MULTISELECT:
            if not isinstance(value, list):
                raise serializers.ValidationError({"value": "Expected list of option keys."})
            if attr.options:
                allowed = set(str(o) for o in attr.options)
                for v in value:
                    if str(v) not in allowed:
                        raise serializers.ValidationError({"value": f"Option not allowed: {v}"})
        else:
            raise serializers.ValidationError({"value": "Unsupported attribute type."})
        return data


class ListingCreateSerializer(serializers.ModelSerializer):
    attributes = ListingAttributeInputSerializer(many=True, required=False)
    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "price_amount",
            "price_currency",
            "is_price_negotiable",
            "condition",
            "deal_type",
            "seller_type",
            "category",
            "location",
            "lat",
            "lon",
            "contact_name",
            "contact_email",
            "contact_phone",
            "attributes",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context["request"].user
        attrs_payload = validated_data.pop("attributes", [])

        # Set default contact info from user profile if not provided
        if hasattr(user, "profile"):
            profile = user.profile
            if not validated_data.get("contact_name") and profile.display_name:
                validated_data["contact_name"] = profile.display_name
            if not validated_data.get("contact_email") and profile.email:
                validated_data["contact_email"] = profile.email
            if not validated_data.get("contact_phone") and profile.phone_e164:
                validated_data["contact_phone"] = profile.phone_e164

        listing = Listing.objects.create(user=user, **validated_data)

        # Simple phone masking from username (which is phone in our OTP flow)
        if hasattr(user, "profile") and user.profile.phone_e164:
            phone = user.profile.phone_e164
        else:
            phone = user.username
        listing.contact_phone_masked = phone #phone[:4] + "****" + phone[-2:]
        listing.save(update_fields=["contact_phone_masked"])
        if attrs_payload:
            self._save_attributes(listing, attrs_payload)
        return listing

    def _save_attributes(self, listing: Listing, attrs_payload: List[Dict[str, Any]]):
        # Determine allowed attributes: listing.category and its ancestors
        allowed_category_ids = set()
        cat = listing.category
        while cat:
            allowed_category_ids.add(cat.id)
            cat = cat.parent  # type: ignore[attr-defined]
        # Fetch all attributes for allowed categories
        attrs = Attribute.objects.filter(category_id__in=allowed_category_ids)
        attrs_by_id = {a.id: a for a in attrs}
        attrs_by_key = {a.key: a for a in attrs}
        # Validate using nested serializer with context
        ser = ListingAttributeInputSerializer(
            data=attrs_payload,
            many=True,
            context={
                "attrs_by_id": attrs_by_id,
                "attrs_by_key": attrs_by_key,
                "lenient": True,
            },
        )
        ser.is_valid(raise_exception=True)
        cleaned = [item for item in ser.validated_data if not item.get("_skip")]
        # Required presence validation across payload
        required_ids = {a.id for a in attrs if a.is_required}
        provided_map = {item["attribute"]: item["value"] for item in cleaned}
        missing: List[str] = []
        for rid in required_ids:
            a = attrs_by_id[rid]
            if rid not in provided_map:
                missing.append(a.key)
                continue
            val = provided_map[rid]
            if a.type in (Attribute.Type.TEXT, Attribute.Type.SELECT) and (val is None or str(val) == ""):
                missing.append(a.key)
            elif a.type == Attribute.Type.MULTISELECT and (not isinstance(val, list) or len(val) == 0):
                missing.append(a.key)
            elif a.type in (Attribute.Type.NUMBER, Attribute.Type.RANGE) and val is None:
                missing.append(a.key)
        if missing:
            # In development, allow creating without all required attributes to keep UX smooth.
            # Set STRICT_ATTRIBUTES=1 to enforce.
            if getattr(settings, "STRICT_ATTRIBUTES", False):
                raise serializers.ValidationError({"attributes": f"Missing required attributes: {', '.join(missing)}"})
            # Otherwise, continue without raising (server will still save provided values)

        # Clear existing
        ListingAttributeValue.objects.filter(listing=listing).delete()
        # Create rows
        bulk: List[ListingAttributeValue] = []
        for item in cleaned:
            attr = attrs_by_id[item["attribute"]]
            value = item["value"]
            if attr.type == Attribute.Type.MULTISELECT:
                for v in value:
                    bulk.append(
                        ListingAttributeValue(
                            listing=listing,
                            attribute=attr,
                            value_option_key=str(v),
                        )
                    )
            elif attr.type == Attribute.Type.SELECT:
                bulk.append(
                    ListingAttributeValue(
                        listing=listing,
                        attribute=attr,
                        value_option_key=str(value),
                    )
                )
            elif attr.type in (Attribute.Type.NUMBER, Attribute.Type.RANGE):
                bulk.append(
                    ListingAttributeValue(
                        listing=listing,
                        attribute=attr,
                        value_number=float(value),
                    )
                )
            elif attr.type == Attribute.Type.BOOLEAN:
                bulk.append(
                    ListingAttributeValue(
                        listing=listing,
                        attribute=attr,
                        value_bool=bool(value),
                    )
                )
            else:  # TEXT
                bulk.append(
                    ListingAttributeValue(
                        listing=listing,
                        attribute=attr,
                        value_text=str(value),
                    )
                )
        if bulk:
            ListingAttributeValue.objects.bulk_create(bulk)


class ListingUpdateSerializer(serializers.ModelSerializer):
    attributes = ListingAttributeInputSerializer(many=True, required=False)

    class Meta:
        model = Listing
        fields = [
            "title",
            "description",
            "price_amount",
            "price_currency",
            "is_price_negotiable",
            "condition",
            "deal_type",
            "seller_type",
            "category",
            "location",
            "lat",
            "lon",
            "contact_name",
            "contact_email",
            "contact_phone",
            "attributes",
        ]

    def validate(self, data):
        """Validate attributes against the target category (new or existing)"""
        attrs_payload = data.get("attributes")
        if not attrs_payload:
            return data

        # Determine which category to validate against
        # Use the new category if provided, otherwise use the instance's current category
        instance = self.instance
        category_id = data.get("category")
        if category_id is None and instance:
            category_id = instance.category_id

        if not category_id:
            return data

        # Get allowed attributes for this category and its ancestors
        allowed_category_ids = set()
        from taxonomy.models import Category
        cat = Category.objects.filter(pk=category_id).first()
        while cat:
            allowed_category_ids.add(cat.id)
            cat = cat.parent

        # Fetch all attributes for allowed categories
        attrs = Attribute.objects.filter(category_id__in=allowed_category_ids)
        attrs_by_id = {a.id: a for a in attrs}
        attrs_by_key = {a.key: a for a in attrs}

        # Validate using nested serializer with context
        ser = ListingAttributeInputSerializer(
            data=attrs_payload,
            many=True,
            context={
                "attrs_by_id": attrs_by_id,
                "attrs_by_key": attrs_by_key,
                "lenient": True,
            },
        )
        ser.is_valid(raise_exception=True)

        # Replace with validated data (with _skip markers)
        data["attributes"] = ser.validated_data
        return data

    def update(self, instance: Listing, validated_data):
        attrs_payload = validated_data.pop("attributes", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if attrs_payload is not None:
            # Recompute allowed attributes with possibly new category
            self._save_attributes(instance, attrs_payload)
        return instance

    def _save_attributes(self, listing: Listing, attrs_payload: List[Dict[str, Any]]):
        # Same logic as in create serializer
        allowed_category_ids = set()
        cat = listing.category
        while cat:
            allowed_category_ids.add(cat.id)
            cat = cat.parent  # type: ignore[attr-defined]
        attrs = Attribute.objects.filter(category_id__in=allowed_category_ids)
        attrs_by_id = {a.id: a for a in attrs}
        attrs_by_key = {a.key: a for a in attrs}
        ser = ListingAttributeInputSerializer(
            data=attrs_payload,
            many=True,
            context={
                "attrs_by_id": attrs_by_id,
                "attrs_by_key": attrs_by_key,
                "lenient": True,
            },
        )
        ser.is_valid(raise_exception=True)
        cleaned = [item for item in ser.validated_data if not item.get("_skip")]
        # Required presence validation across payload
        required_ids = {a.id for a in attrs if a.is_required}
        provided_map = {item["attribute"]: item["value"] for item in cleaned}
        missing: List[str] = []
        for rid in required_ids:
            a = attrs_by_id[rid]
            if rid not in provided_map:
                missing.append(a.key)
                continue
            val = provided_map[rid]
            if a.type in (Attribute.Type.TEXT, Attribute.Type.SELECT) and (val is None or str(val) == ""):
                missing.append(a.key)
            elif a.type == Attribute.Type.MULTISELECT and (not isinstance(val, list) or len(val) == 0):
                missing.append(a.key)
            elif a.type in (Attribute.Type.NUMBER, Attribute.Type.RANGE) and val is None:
                missing.append(a.key)
        if missing:
            if getattr(settings, "STRICT_ATTRIBUTES", False):
                raise serializers.ValidationError({"attributes": f"Missing required attributes: {', '.join(missing)}"})

        ListingAttributeValue.objects.filter(listing=listing).delete()
        bulk: List[ListingAttributeValue] = []
        for item in cleaned:
            attr = attrs_by_id[item["attribute"]]
            value = item["value"]
            if attr.type == Attribute.Type.MULTISELECT:
                for v in value:
                    bulk.append(ListingAttributeValue(listing=listing, attribute=attr, value_option_key=str(v)))
            elif attr.type == Attribute.Type.SELECT:
                bulk.append(ListingAttributeValue(listing=listing, attribute=attr, value_option_key=str(value)))
            elif attr.type in (Attribute.Type.NUMBER, Attribute.Type.RANGE):
                bulk.append(ListingAttributeValue(listing=listing, attribute=attr, value_number=float(value)))
            elif attr.type == Attribute.Type.BOOLEAN:
                bulk.append(ListingAttributeValue(listing=listing, attribute=attr, value_bool=bool(value)))
            else:
                bulk.append(ListingAttributeValue(listing=listing, attribute=attr, value_text=str(value)))
        if bulk:
            ListingAttributeValue.objects.bulk_create(bulk)
