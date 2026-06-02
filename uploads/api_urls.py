from django.urls import path

from .views import PresignUploadView

urlpatterns = [
    path("uploads/presign", PresignUploadView.as_view(), name="uploads-presign"),
]

