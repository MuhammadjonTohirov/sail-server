"""Password-based authentication views (register, login, password reset)."""
from __future__ import annotations

import os
import random
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import OtpCode, Profile
from ..serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)
from .base import PHONE_RE, is_email, normalize_phone


User = get_user_model()


class RegisterView(APIView):
    """Register with email/phone + password, requires OTP confirmation."""
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "otp"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login = ser.validated_data["login"]
        password = ser.validated_data["password"]
        display_name = ser.validated_data.get("display_name", "")

        # Determine if email or phone
        if is_email(login):
            email = login.lower()
            phone = ""
            # Check if email already exists
            if Profile.objects.filter(email=email).exists():
                return Response({"detail": "Email already registered."}, status=400)
        else:
            phone = normalize_phone(login)
            email = ""
            if not PHONE_RE.match(phone):
                return Response({"detail": "Invalid phone format."}, status=400)
            # Check if phone already exists
            if Profile.objects.filter(phone_e164=phone).exists():
                return Response({"detail": "Phone already registered."}, status=400)

        # Generate OTP code
        dev_code = os.environ.get("OTP_DEV_CODE")
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"} and dev_code:
            code = dev_code
        else:
            code = f"{random.randint(0, 999999):06d}"

        # Store registration data temporarily (in real app, use Redis or similar)
        # For now, we'll just create OTP and expect frontend to call verify with all data
        OtpCode.create_new(
            phone=phone,
            email=email,
            code=code,
            purpose=OtpCode.Purpose.LOGIN,
            minutes_valid=5,
            ip=request.META.get("REMOTE_ADDR")
        )

        # Store registration info in session/cache
        # For simplicity, we'll return a token that needs to be sent back
        payload = {"status": "otp_sent", "login": login}
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}:
            payload["debug_code"] = code

        return Response(payload, status=200)


class RegisterVerifyView(APIView):
    """Verify OTP and complete registration."""
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        # Expect: login, code, password, display_name
        login = request.data.get("login")
        code = request.data.get("code")
        password = request.data.get("password")
        display_name = request.data.get("display_name", "")

        if not login or not code or not password:
            return Response({"detail": "Missing required fields."}, status=400)

        # Determine if email or phone
        if is_email(login):
            email = login.lower()
            phone = ""
        else:
            phone = normalize_phone(login)
            email = ""

        now = timezone.now()
        # Find OTP
        if phone:
            otp = OtpCode.objects.filter(
                phone_e164=phone,
                used=False,
                purpose=OtpCode.Purpose.LOGIN
            ).order_by("-created_at").first()
        else:
            otp = OtpCode.objects.filter(
                email=email,
                used=False,
                purpose=OtpCode.Purpose.LOGIN
            ).order_by("-created_at").first()

        if not otp or otp.expires_at < now:
            return Response({"detail": "Code expired or not found."}, status=400)

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return Response({"detail": "Invalid code."}, status=400)

        with transaction.atomic():
            otp.used = True
            otp.save(update_fields=["used"])

            # Create user
            if phone:
                username = phone
            else:
                username = email

            user = User.objects.create_user(username=username, password=password)

            # Create profile
            profile = Profile.objects.create(
                user=user,
                phone_e164=phone,
                email=email,
                display_name=display_name
            )

        # Delete OTP
        otp.delete()

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "profile": ProfileSerializer(profile).data,
        }
        return Response(data, status=200)


class LoginView(APIView):
    """Login with email/phone + password."""
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login = ser.validated_data["login"]
        password = ser.validated_data["password"]

        # Determine if email or phone
        if is_email(login):
            email = login.lower()
            try:
                profile = Profile.objects.get(email=email)
                user = profile.user
            except Profile.DoesNotExist:
                return Response({"detail": "Invalid credentials."}, status=400)
        else:
            phone = normalize_phone(login)
            if not PHONE_RE.match(phone):
                return Response({"detail": "Invalid phone format."}, status=400)
            try:
                profile = Profile.objects.get(phone_e164=phone)
                user = profile.user
            except Profile.DoesNotExist:
                return Response({"detail": "Invalid credentials."}, status=400)

        # Check password
        auth_user = authenticate(username=user.username, password=password)
        if not auth_user:
            return Response({"detail": "Invalid credentials."}, status=400)

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "profile": ProfileSerializer(profile).data,
        }
        return Response(data, status=200)


class ForgotPasswordView(APIView):
    """Request OTP for password reset."""
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "otp"

    def post(self, request):
        ser = ForgotPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login = ser.validated_data["login"]

        # Determine if email or phone
        if is_email(login):
            email = login.lower()
            try:
                profile = Profile.objects.get(email=email)
            except Profile.DoesNotExist:
                # Don't reveal if email exists
                return Response({"status": "sent"}, status=200)
            phone = ""
        else:
            phone = normalize_phone(login)
            if not PHONE_RE.match(phone):
                return Response({"detail": "Invalid phone format."}, status=400)
            try:
                profile = Profile.objects.get(phone_e164=phone)
            except Profile.DoesNotExist:
                # Don't reveal if phone exists
                return Response({"status": "sent"}, status=200)
            email = ""

        # Throttle: max 3 codes per 10 minutes
        ten_min_ago = timezone.now() - timedelta(minutes=10)
        if phone:
            recent_count = OtpCode.objects.filter(
                phone_e164=phone,
                created_at__gte=ten_min_ago,
                purpose=OtpCode.Purpose.PASSWORD_RESET
            ).count()
        else:
            recent_count = OtpCode.objects.filter(
                email=email,
                created_at__gte=ten_min_ago,
                purpose=OtpCode.Purpose.PASSWORD_RESET
            ).count()

        if recent_count >= 3:
            return Response({"detail": "Too many requests. Try later."}, status=429)

        # Generate code
        dev_code = os.environ.get("OTP_DEV_CODE")
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"} and dev_code:
            code = dev_code
        else:
            code = f"{random.randint(0, 999999):06d}"

        OtpCode.create_new(
            phone=phone,
            email=email,
            code=code,
            purpose=OtpCode.Purpose.PASSWORD_RESET,
            minutes_valid=5,
            ip=request.META.get("REMOTE_ADDR")
        )

        payload = {"status": "sent"}
        if os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}:
            payload["debug_code"] = code
        return Response(payload, status=200)


class ResetPasswordView(APIView):
    """Reset password with OTP."""
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login = ser.validated_data["login"]
        code = ser.validated_data["code"]
        password = ser.validated_data["password"]

        # Determine if email or phone
        if is_email(login):
            email = login.lower()
            phone = ""
        else:
            phone = normalize_phone(login)
            email = ""

        now = timezone.now()
        # Find OTP
        if phone:
            otp = OtpCode.objects.filter(
                phone_e164=phone,
                used=False,
                purpose=OtpCode.Purpose.PASSWORD_RESET
            ).order_by("-created_at").first()
        else:
            otp = OtpCode.objects.filter(
                email=email,
                used=False,
                purpose=OtpCode.Purpose.PASSWORD_RESET
            ).order_by("-created_at").first()

        if not otp or otp.expires_at < now:
            return Response({"detail": "Code expired or not found."}, status=400)

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return Response({"detail": "Invalid code."}, status=400)

        # Find user
        if phone:
            try:
                profile = Profile.objects.get(phone_e164=phone)
            except Profile.DoesNotExist:
                return Response({"detail": "User not found."}, status=404)
        else:
            try:
                profile = Profile.objects.get(email=email)
            except Profile.DoesNotExist:
                return Response({"detail": "User not found."}, status=404)

        with transaction.atomic():
            otp.used = True
            otp.save(update_fields=["used"])

            user = profile.user
            user.set_password(password)
            user.save()

        # Delete OTP
        otp.delete()

        return Response({"status": "password_reset"}, status=200)
