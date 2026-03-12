from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist


def get_user_profile(user: Any):
    if not user:
        return None
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


def mask_phone(phone: str) -> str:
    if not phone:
        return ""
    if len(phone) < 5:
        return phone
    return f"{phone[:4]}****{phone[-2:]}"


def sync_listing_contact_phone_mask(listing) -> None:
    listing.contact_phone_masked = mask_phone(listing.contact_phone or "")


def normalize_price_amount(amount: Any, currency: str, rate: Decimal) -> float:
    if amount is None or amount == 0:
        return 0.0
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return float(amount * rate)


def get_listing_contact_details(listing) -> dict[str, str]:
    profile = get_user_profile(getattr(listing, "user", None))
    contact_name = listing.contact_name or getattr(profile, "display_name", "") or ""
    contact_email = listing.contact_email or getattr(profile, "email", "") or ""
    contact_phone = listing.contact_phone or getattr(profile, "phone_e164", "") or ""
    return {
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "contact_phone_masked": mask_phone(contact_phone),
    }
