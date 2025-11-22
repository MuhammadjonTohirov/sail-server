"""Profile management views."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile
from ..serializers import ProfileSerializer, ProfileUpdateSerializer


User = get_user_model()


class MeView(APIView):
    """Get current authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=request.user, phone_e164=request.user.username)
        return Response(ProfileSerializer(profile).data)


class ProfileUpdateView(APIView):
    """Update user profile (display_name, location, logo, banner)."""
    permission_classes = [permissions.IsAuthenticated]

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

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            profile = user.profile
        except (User.DoesNotExist, Profile.DoesNotExist):
            return Response({"detail": "User not found"}, status=404)

        return Response(ProfileSerializer(profile).data, status=200)
