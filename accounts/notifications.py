"""Delivery of OTP / verification codes to users.

Currently supports email delivery (used by registration, password reset, and
the legacy OTP-request flow). Phone/SMS delivery is intentionally a no-op stub
until an SMS provider is wired in -- callers should not assume SMS works yet.

Design notes
------------
* ``send_otp_email`` swallows transport errors and returns a bool so the auth
  views can decide how to respond without leaking SMTP details to the client.
* In DEBUG with the console email backend, the code is printed to stdout, which
  keeps local development working without an SMTP server.
* Never log the OTP code at INFO level in a way that ends up in shared logs;
  the code is only included in the email body and (optionally) the DEBUG API
  response handled by the views themselves.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _purpose_subject(purpose: str, product: str) -> str:
    mapping = {
        "register": f"{product} — confirm your registration",
        "login": f"{product} — your verification code",
        "password_reset": f"{product} — reset your password",
    }
    return mapping.get(purpose, f"{product} — your verification code")


def _purpose_intro(purpose: str) -> str:
    mapping = {
        "register": "Use the code below to finish creating your account.",
        "login": "Use the code below to sign in.",
        "password_reset": "Use the code below to reset your password.",
    }
    return mapping.get(purpose, "Use the code below to continue.")


def send_otp_email(email: str, code: str, purpose: str = "login") -> bool:
    """Send an OTP code to ``email``.

    Returns True if the email was handed to the backend without raising,
    False otherwise. Errors are logged (without the code) and never raised so
    auth endpoints stay resilient to transient SMTP failures.
    """
    if not email:
        return False

    product = getattr(settings, "EMAIL_PRODUCT_NAME", "Sail")
    subject = _purpose_subject(purpose, product)
    intro = _purpose_intro(purpose)
    body = (
        f"{intro}\n\n"
        f"    {code}\n\n"
        "This code expires in 5 minutes. If you did not request it, you can "
        "safely ignore this email.\n\n"
        f"— {product}"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        if sent:
            logger.info("OTP email dispatched purpose=%s to=%s", purpose, _mask(email))
            return True
        logger.warning("OTP email not sent (backend returned 0) purpose=%s to=%s", purpose, _mask(email))
        return False
    except Exception as exc:  # noqa: BLE001 - we deliberately catch all transport errors
        logger.error(
            "Failed to send OTP email purpose=%s to=%s: %s",
            purpose,
            _mask(email),
            exc,
        )
        return False


def _mask(email: str) -> str:
    """Mask an email for logs: ``john.doe@example.com`` -> ``j***@example.com``."""
    try:
        local, domain = email.split("@", 1)
    except ValueError:
        return "***"
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"
