from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ForgotPasswordView,
    LoginView,
    MeView,
    OTPRequestView,
    OTPVerifyView,
    ProfileActiveView,
    ProfileDeleteView,
    ProfileUpdateView,
    RegisterVerifyView,
    RegisterView,
    ResetPasswordView,
    TelegramLoginView,
    UserProfileView,
)

urlpatterns = [
    # Legacy OTP-only auth (kept for backward compatibility)
    path("auth/otp/request", OTPRequestView.as_view(), name="auth-otp-request"),
    path("auth/otp/verify", OTPVerifyView.as_view(), name="auth-otp-verify"),

    # New password-based auth
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/register/verify", RegisterVerifyView.as_view(), name="auth-register-verify"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/forgot-password", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("auth/reset-password", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("auth/telegram", TelegramLoginView.as_view(), name="auth-telegram"),

    # Token refresh
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),

    # Profile endpoints
    path("me", MeView.as_view(), name="me"),
    path("profile", ProfileUpdateView.as_view(), name="profile-update"),
    path("profile/active", ProfileActiveView.as_view(), name="profile-active"),
    path("profile/delete", ProfileDeleteView.as_view(), name="profile-delete"),
    path("users/<int:user_id>", UserProfileView.as_view(), name="user-profile"),
]
