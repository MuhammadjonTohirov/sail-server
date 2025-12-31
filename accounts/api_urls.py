from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AccountSecurityInfoView,
    ChangePasswordView,
    ForgotPasswordView,
    LinkTelegramView,
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
    SetPasswordView,
    TelegramChatConfigViewSet,
    TelegramLoginView,
    TelegramWebhookView,
    UnlinkTelegramView,
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
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),

    # Telegram webhook (public endpoint - no authentication)
    path("webhooks/telegram", TelegramWebhookView.as_view(), name="webhook-telegram"),
    
    # Telegram chat management
    path("telegram-chats/", TelegramChatConfigViewSet.as_view({"get": "list"}), name="telegram-chats"),
    path("telegram-chats/<int:id>/", TelegramChatConfigViewSet.as_view({"get": "retrieve", "delete": "destroy"}), name="telegram-chat-detail"),
    path("telegram-chats/<int:id>/disconnect/", TelegramChatConfigViewSet.as_view({"post": "destroy"}), name="telegram-chat-disconnect"),
    path("telegram-chats/disconnect-all/", TelegramChatConfigViewSet.as_view({"post": "disconnect_all"}), name="telegram-chats-disconnect-all"),
    path("telegram-chats/stats/", TelegramChatConfigViewSet.as_view({"get": "stats"}), name="telegram-chats-stats"),
    path("telegram-chats/verify/", TelegramChatConfigViewSet.as_view({"post": "verify"}), name="telegram-chats-verify"),

    # Profile endpoints
    path("me", MeView.as_view(), name="me"),
    path("profile", ProfileUpdateView.as_view(), name="profile-update"),
    path("profile/active", ProfileActiveView.as_view(), name="profile-active"),
    path("profile/delete", ProfileDeleteView.as_view(), name="profile-delete"),
    path("users/<int:user_id>", UserProfileView.as_view(), name="user-profile"),

    # Security endpoints
    path("security", AccountSecurityInfoView.as_view(), name="security-info"),
    path("security/change-password", ChangePasswordView.as_view(), name="security-change-password"),
    path("security/set-password", SetPasswordView.as_view(), name="security-set-password"),
    path("security/link-telegram", LinkTelegramView.as_view(), name="security-link-telegram"),
    path("security/unlink-telegram", UnlinkTelegramView.as_view(), name="security-unlink-telegram"),
]
