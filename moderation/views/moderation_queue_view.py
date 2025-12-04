from __future__ import annotations

from rest_framework import generics, permissions

from ..models import Report
from ..serializers import ReportSerializer


class ModerationQueueView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Report.objects.filter(status=Report.Status.OPEN).order_by("-created_at")
