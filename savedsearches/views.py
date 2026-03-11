from __future__ import annotations

from typing import Any, Dict

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SavedSearch
from .serializers import SavedSearchSerializer
from searchapp.views.opensearch_client import get_client
from searchapp.views.index import index_name


@extend_schema(
    tags=["saved-searches"],
    summary="List or create saved searches",
    description="List all saved searches for the authenticated user or create a new one.",
    examples=[
        OpenApiExample(
            "Success",
            value={"success": True, "data": [{"id": 1, "query": {"q": "iphone"}, "frequency": "daily", "is_active": True}], "error": None, "code": 200},
            response_only=True,
        ),
    ],
)
class SavedSearchListCreateView(generics.ListCreateAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(
    tags=["saved-searches"],
    summary="Retrieve, update, or delete a saved search",
    description="Retrieve, update, or delete a specific saved search by ID.",
    examples=[
        OpenApiExample(
            "Success",
            value={"success": True, "data": {"id": 1, "query": {"q": "iphone"}, "frequency": "daily", "is_active": True}, "error": None, "code": 200},
            response_only=True,
        ),
    ],
)
class SavedSearchDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)


class SavedSearchMarkViewedView(APIView):
    """Mark a saved search as viewed (updates last_viewed_at)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["saved-searches"],
        summary="Mark saved search as viewed",
        description="Update the last_viewed_at timestamp for a saved search.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"success": True, "last_viewed_at": "2025-01-01T00:00:00Z"}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def post(self, request, pk: int):
        from django.utils import timezone

        try:
            saved = SavedSearch.objects.get(id=pk, user=request.user)
        except SavedSearch.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        saved.last_viewed_at = timezone.now()
        saved.save(update_fields=["last_viewed_at"])

        return Response({"success": True, "last_viewed_at": saved.last_viewed_at})


class SavedSearchRunNowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["saved-searches"],
        summary="Run a saved search now",
        description="Execute a saved search immediately and return a sample of results.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"total": 15, "sample": ["iPhone 15", "Samsung Galaxy"]}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def post(self, request, pk: int):
        try:
            saved = SavedSearch.objects.get(id=pk, user=request.user, is_active=True)
        except SavedSearch.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        client = get_client()
        if not client:
            return Response({"results": [], "total": 0, "note": "OpenSearch not configured"})

        q: Dict[str, Any] = saved.query or {}
        body = q.get("body")
        if not body:
            # If user stored a param bag, translate to a simple bool
            params = q.get("params", {})
            must = []
            if kw := params.get("q"):
                must.append({"multi_match": {"query": kw, "fields": ["title^2", "description"]}})
            body = {"query": {"bool": {"must": must}}}
        resp = client.search(index=index_name(), body=body)
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)
        return Response({"total": total, "sample": [h.get("_source", {}).get("title") for h in hits[:5]]})

