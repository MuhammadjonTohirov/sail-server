from __future__ import annotations

from rest_framework import serializers

from .models import SavedSearch
from .utils import count_new_items_for_saved_search


class SavedSearchSerializer(serializers.ModelSerializer):
    new_items_count = serializers.SerializerMethodField()

    class Meta:
        model = SavedSearch
        fields = ["id", "title", "query", "frequency", "is_active", "last_sent_at", "last_viewed_at", "created_at", "new_items_count"]
        read_only_fields = ["new_items_count"]

    def get_new_items_count(self, obj: SavedSearch) -> int:
        """Get count of new items since last viewed."""
        return count_new_items_for_saved_search(obj)

