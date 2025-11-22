"""OTP-based authentication views."""
from __future__ import annotations

import os
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import OtpCode, Profile
from ..serializers import OTPRequestSerializer, OTPVerifySerializer, ProfileSerializer
from .base import PHONE_RE, normalize_phone


User = get_user_model()


class OTPRequestView(APIView):
    """Request OTP code for phone-based authentication."""
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "otp"

    def post(self, request):
        ser = OTPRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = normalize_phone(ser.validated_data["phone"])
        if not PHONE_RE.match(phone):
            return Response({"detail": "Invalid phone format."}, status=400)

        # Throttle: max 3 codes per 10 minutes per phone
        ten_min_ago = timezone.now() - timedelta(minutes=10)
        recent_count = OtpCode.objects.filter(phone_e164=phone, created_at__gte=ten_min_ago).count()
        if recent_count >= 3:
            return Response({"detail": "Too many requests. Try later."}, status=429)

        # Generate code
        dev_code = os.environ.get("OTP_DEV_CODE")
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"} and dev_code:
            code = dev_code
        else:
            code = f"{random.randint(0, 999999):06d}"

        OtpCode.create_new(phone=phone, code=code, minutes_valid=5, ip=request.META.get("REMOTE_ADDR"))

        payload = {"status": "sent"}
        # In DEBUG, optionally return code for convenience
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}:
            payload["debug_code"] = code
        return Response(payload, status=200)


class OTPVerifyView(APIView):
    """Verify OTP code and authenticate user."""
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "otp"

    def post(self, request):
        ser = OTPVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = normalize_phone(ser.validated_data["phone"])
        code = ser.validated_data["code"]

        now = timezone.now()
        # Pick the latest non-used code
        otp = (
            OtpCode.objects.filter(phone_e164=phone, used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.expires_at < now:
            return Response({"detail": "Code expired or not found."}, status=400)
        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return Response({"detail": "Invalid code."}, status=400)

        with transaction.atomic():
            otp.used = True
            otp.save(update_fields=["used"])
            user, created = User.objects.get_or_create(username=phone)
            if created:
                user.set_unusable_password()
                user.save()
            profile, _ = Profile.objects.get_or_create(user=user, defaults={"phone_e164": phone})
            if profile.phone_e164 != phone:
                profile.phone_e164 = phone
                profile.save(update_fields=["phone_e164"])

        # delete otp after successful verification
        otp.delete()

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "profile": ProfileSerializer(profile).data,
        }
        return Response(data, status=200)
