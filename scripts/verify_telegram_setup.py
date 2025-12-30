#!/usr/bin/env python
"""
Verification script for Telegram cross-posting setup.
Run this script to check if all components are properly configured.

Usage:
    cd server
    python scripts/verify_telegram_setup.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from accounts.models import TelegramChatConfig
from listings.models import Listing
import requests


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def check_mark(condition):
    return "✓" if condition else "✗"


def verify_settings():
    """Verify Django settings configuration."""
    print_header("1. Django Settings Verification")

    checks = []

    # Check TELEGRAM_BOT_TOKEN
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    token_set = bool(bot_token and len(bot_token) > 0)
    checks.append(("TELEGRAM_BOT_TOKEN", token_set))
    print(f"{check_mark(token_set)} TELEGRAM_BOT_TOKEN: {'SET' if token_set else 'NOT SET'}")
    if token_set:
        print(f"   Token: {bot_token[:10]}...{bot_token[-10:] if len(bot_token) > 20 else ''}")

    # Check WEB_BASE_URL
    web_url = getattr(settings, 'WEB_BASE_URL', None)
    url_set = bool(web_url)
    checks.append(("WEB_BASE_URL", url_set))
    print(f"{check_mark(url_set)} WEB_BASE_URL: {web_url if url_set else 'NOT SET'}")

    # Check Celery broker
    broker_url = getattr(settings, 'CELERY_BROKER_URL', None) or \
                 os.environ.get('CELERY_BROKER_URL') or \
                 os.environ.get('REDIS_URL')
    broker_set = bool(broker_url and not broker_url.startswith('memory://'))
    checks.append(("Celery Broker", broker_set))
    print(f"{check_mark(broker_set)} Celery Broker: {broker_url if broker_url else 'NOT SET'}")

    if not broker_set:
        print("   ⚠ Warning: Using in-memory broker. Celery tasks will run synchronously.")
        print("   For production, set REDIS_URL or CELERY_BROKER_URL environment variable.")

    return all(status for _, status in checks)


def verify_telegram_chats():
    """Verify Telegram chat configurations."""
    print_header("2. Telegram Chat Configurations")

    total_chats = TelegramChatConfig.objects.count()
    active_chats = TelegramChatConfig.objects.filter(is_active=True)

    print(f"Total Telegram chats: {total_chats}")
    print(f"Active chats: {active_chats.count()}\n")

    if active_chats.count() == 0:
        print("✗ No active Telegram chats found!")
        print("\nTo add Telegram chats:")
        print("1. Add your bot (@sail2_bot) to Telegram channels/groups")
        print("2. Send /start message to the bot from the channel")
        print("3. The webhook should automatically register the chat")
        return False

    print("Active Telegram Chats:")
    for chat in active_chats:
        print(f"\n  {check_mark(True)} {chat.chat_title}")
        print(f"     Type: {chat.chat_type}")
        print(f"     Chat ID: {chat.chat_id}")
        print(f"     Username: @{chat.chat_username}" if chat.chat_username else "     Username: (none)")
        print(f"     Photo: {check_mark(bool(chat.chat_photo))} {'SET' if chat.chat_photo else 'NOT SET'}")
        print(f"     Created: {chat.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    return True


def verify_bot_connection():
    """Verify Telegram bot API connection."""
    print_header("3. Telegram Bot API Connection")

    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not bot_token:
        print("✗ Cannot test bot connection: TELEGRAM_BOT_TOKEN not set")
        return False

    try:
        # Test getMe endpoint
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )

        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                result = bot_info.get('result', {})
                print(f"✓ Bot connection successful!")
                print(f"   Bot name: @{result.get('username')}")
                print(f"   Bot ID: {result.get('id')}")
                print(f"   First name: {result.get('first_name')}")
                return True

        print(f"✗ Bot connection failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    except Exception as e:
        print(f"✗ Error connecting to Telegram API: {e}")
        return False


def verify_celery_tasks():
    """Verify Celery task registration."""
    print_header("4. Celery Task Registration")

    try:
        from listings.tasks import share_listing_to_telegram_task
        print(f"✓ Task 'share_listing_to_telegram_task' is registered")
        print(f"   Task name: {share_listing_to_telegram_task.name}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import Celery task: {e}")
        return False


def verify_listing_model():
    """Verify listing model and serializer support."""
    print_header("5. Listing Model & Serializer")

    # Check if ListingCreateSerializer has sharing_telegram_chat_ids
    try:
        from listings.serializers import ListingCreateSerializer
        serializer = ListingCreateSerializer()
        has_field = 'sharing_telegram_chat_ids' in serializer.fields
        print(f"{check_mark(has_field)} ListingCreateSerializer has 'sharing_telegram_chat_ids' field")

        if not has_field:
            print("   Available fields:", list(serializer.fields.keys())[:10], "...")

        return has_field
    except Exception as e:
        print(f"✗ Error checking serializer: {e}")
        return False


def verify_api_endpoint():
    """Verify Telegram chats API endpoint."""
    print_header("6. API Endpoint Verification")

    try:
        from django.urls import reverse
        url = reverse('telegram-chats-list')
        print(f"✓ API endpoint registered: {url}")
        print(f"   Full URL: http://localhost:8000{url}")
        return True
    except Exception as e:
        print(f"✗ API endpoint not found: {e}")
        return False


def print_summary(results):
    """Print final summary."""
    print_header("Summary")

    passed = sum(results.values())
    total = len(results)

    print(f"Checks passed: {passed}/{total}\n")

    for check, status in results.items():
        print(f"{check_mark(status)} {check}")

    print("\n" + "=" * 60)

    if passed == total:
        print("\n✓ All checks passed! Telegram cross-posting is ready to test.")
        print("\nNext steps:")
        print("1. Start Celery worker: celery -A config worker --loglevel=info")
        print("2. Navigate to frontend post page: http://localhost:3000/post")
        print("3. Create a listing and select Telegram channels")
        print("4. Monitor Celery logs for task execution")
        print("5. Check Telegram channels for posted messages")
    else:
        print("\n✗ Some checks failed. Please review the output above.")
        print("\nRefer to TESTING_TELEGRAM_CROSSPOSTING.md for detailed troubleshooting.")


def main():
    print("\n" + "=" * 60)
    print("  Telegram Cross-Posting Setup Verification")
    print("=" * 60)

    results = {
        "Settings Configuration": verify_settings(),
        "Telegram Chats": verify_telegram_chats(),
        "Bot API Connection": verify_bot_connection(),
        "Celery Task Registration": verify_celery_tasks(),
        "Listing Serializer": verify_listing_model(),
        "API Endpoint": verify_api_endpoint(),
    }

    print_summary(results)


if __name__ == "__main__":
    main()
