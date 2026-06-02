from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions


class PresignUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["uploads"],
        summary="Get presigned upload URL",
        description="Get a presigned S3 upload URL for direct file uploads. Falls back to local upload mode if S3 is not configured.",
        examples=[
            OpenApiExample(
                "S3 mode",
                value={"success": True, "data": {"mode": "s3", "presigned": {"url": "https://s3.example.com/bucket", "fields": {}}, "public_url": "https://s3.example.com/bucket/uploads/abc123"}, "error": None, "code": 200},
                response_only=True,
            ),
            OpenApiExample(
                "Local mode",
                value={"success": True, "data": {"mode": "local", "message": "S3 not configured; use local upload endpoint"}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        # If S3 env is configured, return a presigned POST; else, indicate local upload
        bucket = os.environ.get("MEDIA_BUCKET")
        endpoint = os.environ.get("MEDIA_ENDPOINT") or os.environ.get("AWS_S3_ENDPOINT_URL")
        access_key = os.environ.get("MEDIA_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("MEDIA_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("AWS_REGION")
        key_prefix = os.environ.get("MEDIA_PREFIX", "uploads/")

        if not (bucket and access_key and secret_key and endpoint):
            return Response({
                "mode": "local",
                "message": "S3 not configured; use local upload endpoint /api/v1/listings/<id>/media",
            })

        try:
            import boto3  # type: ignore
        except Exception:
            return Response({"mode": "local", "message": "boto3 missing; install server requirements"}, status=200)

        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        key = f"{key_prefix}{uuid.uuid4().hex}"
        conditions = [["content-length-range", 0, 10 * 1024 * 1024]]
        fields = {"acl": "public-read"}
        presigned = s3.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=3600,
        )
        return Response({"mode": "s3", "presigned": presigned, "public_url": f"{endpoint}/{bucket}/{key}"})

