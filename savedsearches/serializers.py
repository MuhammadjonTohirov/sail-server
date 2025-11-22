from __future__ import annotations

from rest_framework import serializers

from .models import SavedSearch


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ["id", "title", "query", "frequency", "is_active", "last_sent_at", "created_at"]

