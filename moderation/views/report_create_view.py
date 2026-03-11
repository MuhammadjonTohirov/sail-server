from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions

from ..serializers import ReportCreateSerializer


@extend_schema(
    tags=["moderation"],
    summary="Submit a report",
    description="Submit a report for a listing. Can be used by authenticated and anonymous users.",
    examples=[
        OpenApiExample(
            "Success",
            value={"success": True, "data": {"listing": 10, "reason_code": "fraud", "notes": "Suspicious listing"}, "error": None, "code": 201},
            response_only=True,
        ),
    ],
)
class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        reporter = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(reporter=reporter)
