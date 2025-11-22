from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "reporter", "reason_code", "status", "created_at")
    list_filter = ("status", "reason_code")
    search_fields = ("notes", "reason_code", "listing__title")
    autocomplete_fields = ("listing", "reporter")

