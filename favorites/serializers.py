from rest_framework import serializers

from .models import FavoriteListing, RecentlyViewedListing


class FavoriteListingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_price = serializers.DecimalField(
        source="listing.price_amount",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    listing_location = serializers.CharField(source="listing.location.name", read_only=True)
    listing_media_urls = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteListing
        fields = [
            "id",
            "listing",
            "listing_title",
            "listing_price",
            "listing_location",
            "listing_media_urls",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_listing_media_urls(self, obj):
        media = obj.listing.media.all()[:1]  # Get first image
        request = self.context.get('request')
        if media and request:
            return [request.build_absolute_uri(m.image.url) for m in media]
        elif media:
            return [m.image.url for m in media]
        return []


class RecentlyViewedListingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_price = serializers.DecimalField(
        source="listing.price_amount",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    listing_location = serializers.CharField(source="listing.location.name", read_only=True)
    listing_media_urls = serializers.SerializerMethodField()

    class Meta:
        model = RecentlyViewedListing
        fields = [
            "id",
            "listing",
            "listing_title",
            "listing_price",
            "listing_location",
            "listing_media_urls",
            "viewed_at",
        ]
        read_only_fields = ["id", "viewed_at"]

    def get_listing_media_urls(self, obj):
        media = obj.listing.media.all()[:1]  # Get first image
        request = self.context.get('request')
        if media and request:
            return [request.build_absolute_uri(m.image.url) for m in media]
        elif media:
            return [m.image.url for m in media]
        return []
