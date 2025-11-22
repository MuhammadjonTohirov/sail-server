from rest_framework import serializers

from .models import Attribute, Category, Location


class AttributeSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = [
            "id",
            "key",
            "label",
            "type",
            "unit",
            "options",
            "is_indexed",
            "is_required",
            "min_number",
            "max_number",
        ]

    def get_label(self, obj):  # pragma: no cover
        lang = (self.context or {}).get("lang")
        if not lang and self.context and self.context.get("request"):
            lang = self.context["request"].query_params.get("lang")
        if lang == "uz":
            return obj.label_uz or obj.label or obj.label_ru
        # default ru
        return obj.label_ru or obj.label or obj.label_uz


class CategoryNodeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    is_leaf = serializers.BooleanField()
    order = serializers.IntegerField()
    icon = serializers.CharField(required=False, allow_blank=True)
    icon_url = serializers.CharField(required=False, allow_blank=True)
    children = serializers.ListField(child=serializers.DictField(), allow_empty=True)


class LocationSerializer(serializers.ModelSerializer):
    has_children = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ["id", "name", "name_ru", "name_uz", "slug", "kind", "lat", "lon", "has_children", "parent"]

    def get_has_children(self, obj):  # pragma: no cover
        return obj.children.exists()

    def get_name(self, obj):  # pragma: no cover
        request = self.context.get("request") if self.context else None
        lang = None
        if request:
            lang = request.query_params.get("lang")
        if lang == "uz":
            return obj.name_uz or obj.name or obj.name_ru
        return obj.name_ru or obj.name or obj.name_uz
