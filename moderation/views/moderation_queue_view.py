from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions

from ..models import Report
from ..serializers import ReportSerializer


@extend_schema(
    tags=["moderation"],
    summary="List moderation queue",
    description="List all open reports in the moderation queue. Admin only.",
    examples=[
        OpenApiExample(
            "Success",
            value={"success": True, "data": [{"id": 1, "listing": 10, "reporter": 5, "reason_code": "fraud", "status": "open", "created_at": "2025-01-01T00:00:00Z"}], "error": None, "code": 200},
            response_only=True,
        ),
    ],
)
class ModerationQueueView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Report.objects.filter(status=Report.Status.OPEN).order_by("-created_at")
