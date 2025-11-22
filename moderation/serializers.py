from __future__ import annotations

from rest_framework import serializers

from .models import Report


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["listing", "reason_code", "notes"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "listing", "reporter", "reason_code", "notes", "status", "created_at"]

