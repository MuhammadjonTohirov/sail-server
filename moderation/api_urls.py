from django.urls import path

from .views import ModerationQueueView, ReportCreateView, ReportReasonsView

urlpatterns = [
    path("reports", ReportCreateView.as_view(), name="report-create"),
    path("reports/reasons", ReportReasonsView.as_view(), name="report-reasons"),
    path("moderation/queue", ModerationQueueView.as_view(), name="moderation-queue"),
]
