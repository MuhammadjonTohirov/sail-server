"""Base utilities for authentication views."""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile


logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")


def normalize_phone(raw: str) -> str:
    """Normalize phone number format."""
    s = re.sub(r"\s+|[-()]", "", raw)
    if not s.startswith("+"):
        # naive assumption: if missing +, accept as given; real impl should use phonenumbers
        s = "+" + s
    return s


def is_email(login: str) -> bool:
    """Check if login is email format."""
    return "@" in login


def download_telegram_photo(photo_url: str, telegram_id: int) -> ContentFile | None:
    """
    Download Telegram profile photo and return as ContentFile.
    Returns None if download fails.
    """
    if not photo_url:
        return None

    try:
        response = requests.get(photo_url, timeout=10, stream=True)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            logger.warning(f"Invalid content type for Telegram photo: {content_type}")
            return None

        # Check file size (max 5MB)
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 5 * 1024 * 1024:
            logger.warning(f"Telegram photo too large: {content_length} bytes")
            return None

        # Read content
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 5 * 1024 * 1024:
                logger.warning("Telegram photo exceeded size limit during download")
                return None

        # Determine extension from URL or content-type
        ext = 'jpg'
        parsed_url = urlparse(photo_url)
        if '.' in parsed_url.path:
            ext = parsed_url.path.split('.')[-1].lower()
        elif 'jpeg' in content_type:
            ext = 'jpg'
        elif 'png' in content_type:
            ext = 'png'

        filename = f"tg_{telegram_id}_avatar.{ext}"
        return ContentFile(content, name=filename)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download Telegram photo from {photo_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading Telegram photo: {e}")
        return None
