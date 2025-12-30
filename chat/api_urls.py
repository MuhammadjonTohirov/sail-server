from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChatAttachmentUploadView,
    ChatThreadViewSet,
    SyncChatAvailabilityView,
    BulkListingStatusView,
)

router = DefaultRouter()
router.register(r"chat/threads", ChatThreadViewSet, basename="chat-threads")

urlpatterns = router.urls + [
    path("chat/threads/<uuid:id>/attachments/", ChatAttachmentUploadView.as_view(), name="chat-thread-attachments"),
    path("chat/sync-availability", SyncChatAvailabilityView.as_view(), name="chat-sync-availability"),
    path("listings/status/bulk", BulkListingStatusView.as_view(), name="listings-status-bulk"),
]
