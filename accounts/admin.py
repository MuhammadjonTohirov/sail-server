from django.contrib import admin

from .models import OtpCode, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_e164", "display_name", "created_at")
    search_fields = ("phone_e164", "display_name", "user__username", "user__email")


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ("phone_e164", "code", "created_at", "expires_at", "used", "attempts")
    list_filter = ("used",)
    search_fields = ("phone_e164",)

