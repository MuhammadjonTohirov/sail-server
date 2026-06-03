"""Regression tests for auth fixes: Telegram login HMAC + OTP email delivery."""
from __future__ import annotations

import hashlib
import hmac

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import OtpCode, Profile

BOT_TOKEN = "test-bot-token-123456:ABCDEF"


def telegram_sign(payload: dict, token: str) -> str:
    """Replicate Telegram's data_check_string signing over the given fields."""
    pairs = [f"{k}={payload[k]}" for k in sorted(payload) if k != "hash"]
    dcs = "\n".join(pairs)
    secret = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN, DEBUG=False)
class TelegramLoginHashTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-telegram")

    def _base_payload(self):
        # Use a far-future auth_date so the max-age check passes regardless of clock.
        import time

        return {
            "id": 987654321,
            "first_name": "Alice",
            "username": "alice",
            "auth_date": int(time.time()),
        }

    def test_valid_signature_logs_in(self):
        payload = self._base_payload()
        payload["hash"] = telegram_sign(payload, BOT_TOKEN)
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(Profile.objects.filter(telegram_id=987654321).exists())

    def test_blank_optional_fields_do_not_break_signature(self):
        """Regression: frontend forwards empty last_name/photo_url that Telegram
        never signed. Login must still succeed because the server ignores
        empty optional fields when rebuilding the data_check_string."""
        payload = self._base_payload()
        # Telegram signed ONLY the real fields:
        payload["hash"] = telegram_sign(payload, BOT_TOKEN)
        # Frontend adds empty optionals before posting:
        payload["last_name"] = ""
        payload["photo_url"] = ""
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_tampered_signature_rejected(self):
        payload = self._base_payload()
        payload["hash"] = "deadbeef" * 8
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)


@override_settings(
    DEBUG=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Sail <no-reply@sail.uz>",
)
class RegistrationEmailDeliveryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_sends_otp_email(self):
        mail.outbox = []
        url = reverse("auth-register")
        resp = self.client.post(
            url,
            {"login": "newuser@example.com", "password": "Sup3rSecret!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        # An OTP row was created...
        otp = OtpCode.objects.filter(email="newuser@example.com").order_by("-created_at").first()
        self.assertIsNotNone(otp)
        # ...and an email carrying that code was sent.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("newuser@example.com", msg.to)
        self.assertIn(otp.code, msg.body)

    def test_forgot_password_sends_email_for_existing_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="exists@example.com", password="x")
        Profile.objects.create(user=user, email="exists@example.com")

        mail.outbox = []
        url = reverse("auth-forgot-password")
        resp = self.client.post(url, {"login": "exists@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(mail.outbox), 1)
        otp = (
            OtpCode.objects.filter(
                email="exists@example.com", purpose=OtpCode.Purpose.PASSWORD_RESET
            )
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(otp)
        self.assertIn(otp.code, mail.outbox[0].body)

    def test_forgot_password_unknown_email_sends_nothing_but_returns_ok(self):
        mail.outbox = []
        url = reverse("auth-forgot-password")
        resp = self.client.post(url, {"login": "nobody@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(mail.outbox), 0)
