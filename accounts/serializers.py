from django.contrib.auth.models import User
from rest_framework import serializers

from . import models
from .models import Profile


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)


class RegisterSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=255, help_text="Phone number or email")
    password = serializers.CharField(max_length=128, write_only=True)
    display_name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=255, help_text="Phone number or email")
    password = serializers.CharField(max_length=128, write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=255, help_text="Phone number or email")


class ResetPasswordSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=255, help_text="Phone number or email")
    code = serializers.CharField(max_length=6)
    password = serializers.CharField(max_length=128, write_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    location_id = serializers.IntegerField(source="location.id", read_only=True, allow_null=True)
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "user_id",
            "username",
            "phone_e164",
            "email",
            "display_name",
            "avatar_url",
            "about",
            "location_id",
            "location_name",
            "logo",
            "banner",
            "telegram_id",
            "telegram_username",
            "telegram_photo_url",
            "last_active_at",
            "created_at",
        ]
        read_only_fields = ["phone_e164", "created_at", "telegram_id", "telegram_username", "telegram_photo_url"]

    def get_location_name(self, obj):
        if obj.location:
            # Return full path like "Ташкент > Мирзо-Улугбекский район"
            parts = []
            loc = obj.location
            while loc:
                parts.insert(0, loc.name)
                loc = loc.parent if hasattr(loc, 'parent') else None
            return " > ".join(parts) if parts else obj.location.name
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    location = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Profile
        fields = ["display_name", "email", "location", "logo", "banner"]

    def update(self, instance, validated_data):
        # Handle location separately
        location_id = validated_data.pop("location", None)
        if location_id is not None:
            if location_id:
                from taxonomy.models import Location
                try:
                    location = Location.objects.get(id=location_id)
                    instance.location = location
                except Location.DoesNotExist:
                    raise serializers.ValidationError({"location": "Location not found"})
            else:
                instance.location = None

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class TelegramLoginSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(required=False, allow_blank=True)
    auth_date = serializers.IntegerField()
    hash = serializers.CharField()


class TelegramChatConfigSerializer(serializers.ModelSerializer):
    """Serializer for reading Telegram chat configurations."""
    chat_photo = serializers.SerializerMethodField()

    class Meta:
        model = models.TelegramChatConfig
        fields = [
            "id",
            "chat_id",
            "chat_type",
            "chat_title",
            "chat_username",
            "chat_photo",
            "is_active",
            "bot_status",
            "created_at",
            "updated_at",
            "last_verified_at",
        ]
        read_only_fields = fields  # All fields are read-only (webhook-managed)

    def get_chat_photo(self, obj):
        if obj.chat_photo:
            return obj.chat_photo.url
        return None
