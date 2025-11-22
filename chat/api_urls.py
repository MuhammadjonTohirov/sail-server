from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatAttachmentUploadView, ChatThreadViewSet

router = DefaultRouter()
router.register(r"chat/threads", ChatThreadViewSet, basename="chat-threads")

urlpatterns = router.urls + [
    path("chat/threads/<uuid:id>/attachments/", ChatAttachmentUploadView.as_view(), name="chat-thread-attachments"),
]
