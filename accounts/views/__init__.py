"""Export all views from submodules."""

# OTP authentication
from .otp_auth import OTPRequestView, OTPVerifyView

# Password authentication
from .password_auth import (
    ForgotPasswordView,
    LoginView,
    RegisterVerifyView,
    RegisterView,
    ResetPasswordView,
)

# Profile management
from .profile import (
    MeView,
    ProfileActiveView,
    ProfileDeleteView,
    ProfileUpdateView,
    UserProfileView,
)

# Telegram authentication
from .telegram_auth import TelegramLoginView

# Telegram webhook
from .telegram_webhook import TelegramWebhookView

# Telegram chat management
from .telegram_chat_config import TelegramChatConfigViewSet

__all__ = [
    # OTP
    "OTPRequestView",
    "OTPVerifyView",
    # Password
    "RegisterView",
    "RegisterVerifyView",
    "LoginView",
    "ForgotPasswordView",
    "ResetPasswordView",
    # Telegram
    "TelegramLoginView",
    "TelegramWebhookView",
    "TelegramChatConfigViewSet",
    # Profile
    "MeView",
    "ProfileUpdateView",
    "ProfileDeleteView",
    "ProfileActiveView",
    "UserProfileView",
]
