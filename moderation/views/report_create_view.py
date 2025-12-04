from __future__ import annotations

from rest_framework import generics, permissions

from ..serializers import ReportCreateSerializer


class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        reporter = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(reporter=reporter)
