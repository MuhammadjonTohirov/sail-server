from __future__ import annotations

import mimetypes
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ChatThread


class ChatAttachmentUploadView(APIView):
    parser_classes = (MultiPartParser,)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id: uuid.UUID):
        try:
            thread = ChatThread.objects.prefetch_related("participants").get(id=id)
        except ChatThread.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not thread.participants.filter(user_id=request.user.id, is_deleted=False).exists():
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        filename = os.path.basename(file_obj.name) or "attachment"
        storage_path = os.path.join("chat_attachments", str(thread.id), f"{uuid.uuid4().hex}_{filename}")
        saved_path = default_storage.save(storage_path, file_obj)

        if settings.MEDIA_URL.startswith("http://") or settings.MEDIA_URL.startswith("https://"):
            base = settings.MEDIA_URL.rstrip("/")
            public_url = f"{base}/{saved_path}"
        else:
            public_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

        content_type = file_obj.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        attachment_type = "image" if content_type.startswith("image/") else "file"

        payload = {
            "type": attachment_type,
            "url": public_url,
            "name": filename,
            "size": file_obj.size,
            "content_type": content_type,
        }
        return Response(payload, status=status.HTTP_201_CREATED)
