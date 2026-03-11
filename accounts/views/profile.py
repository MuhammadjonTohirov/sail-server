"""Profile management views."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile
from ..serializers import ProfileSerializer, ProfileUpdateSerializer


User = get_user_model()


class MeView(APIView):
    """Get current authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["profile"],
        summary="Get current user profile",
        description="Return the authenticated user's profile. Creates a profile if one does not exist.",
        responses={200: ProfileSerializer},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "user_id": 1,
                        "username": "+998901234567",
                        "display_name": "John",
                        "email": "user@example.com",
                        "phone_e164": "+998901234567",
                        "last_active_at": "2026-03-11T12:00:00Z",
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=request.user, phone_e164=request.user.username)
        return Response(ProfileSerializer(profile).data)


class ProfileUpdateView(APIView):
    """Update user profile (display_name, location, logo, banner)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["profile"],
        summary="Update user profile",
        description="Partially update the authenticated user's profile fields such as display_name, location, logo, and banner.",
        request=ProfileUpdateSerializer,
        responses={200: ProfileSerializer, 404: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"user_id": 1, "display_name": "New Name", "email": "user@example.com"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Not found",
                value={"success": False, "data": None, "error": "Profile not found", "code": 404},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def patch(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found"}, status=404)

        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return full profile data
        return Response(ProfileSerializer(profile).data, status=200)


class ProfileDeleteView(APIView):
    """Delete user account and all associated data."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["profile"],
        summary="Delete user account",
        description="Permanently delete the authenticated user's account and all associated data. This action is irreversible.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {
                        "status": "deleted",
                        "user_id": 1,
                        "message": "Account and all associated data have been permanently deleted.",
                    },
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def delete(self, request):
        user = request.user

        # Delete user (will cascade to profile and listings via on_delete=CASCADE)
        user_id = user.id
        user.delete()

        return Response({
            "status": "deleted",
            "user_id": user_id,
            "message": "Account and all associated data have been permanently deleted."
        }, status=200)


class ProfileActiveView(APIView):
    """Mark authenticated user as active right now."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["profile"],
        summary="Mark user as active",
        description="Update the authenticated user's last_active_at timestamp to the current time.",
        responses={200: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"last_active_at": "2026-03-11T12:00:00Z"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=request.user, phone_e164=request.user.username)
        profile.last_active_at = timezone.now()
        profile.save(update_fields=["last_active_at"])
        return Response({"last_active_at": profile.last_active_at}, status=200)


class UserProfileView(APIView):
    """Get user profile by user ID (public endpoint)."""
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        tags=["profile"],
        summary="Get user profile by ID",
        description="Return a public user profile by user ID. No authentication required.",
        responses={200: ProfileSerializer, 404: None},
        examples=[
            OpenApiExample(
                "Success",
                value={
                    "success": True,
                    "data": {"user_id": 42, "display_name": "Jane", "last_active_at": "2026-03-11T12:00:00Z"},
                    "error": None,
                    "code": 200,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Not found",
                value={"success": False, "data": None, "error": "User not found", "code": 404},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            profile = user.profile
        except (User.DoesNotExist, Profile.DoesNotExist):
            return Response({"detail": "User not found"}, status=404)

        return Response(ProfileSerializer(profile).data, status=200)
