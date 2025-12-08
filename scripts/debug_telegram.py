import os
import sys
import requests
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def check_telegram_webhook():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or token == "your_telegram_bot_token":
        print("❌ TELEGRAM_BOT_TOKEN is not set or is default in settings.")
        return

    print(f"🔹 Checking Telegram Bot: {token[:5]}...{token[-5:]}")
    
    # 1. Get Me (Check Bot)
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        response.raise_for_status()
        bot_info = response.json()
        if bot_info.get("ok"):
            print(f"✅ Bot found: @{bot_info['result']['username']} (ID: {bot_info['result']['id']})")
        else:
            print(f"❌ Failed to get bot info: {bot_info}")
            return
    except Exception as e:
        print(f"❌ Error connecting to Telegram API: {e}")
        return

    # 2. Get Webhook Info
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        response.raise_for_status()
        webhook_info = response.json()
        if webhook_info.get("ok"):
            result = webhook_info['result']
            url = result.get('url')
            print(f"\n🔹 Webhook Status:")
            if url:
                print(f"   ✅ URL: {url}")
                print(f"   • Has Custom Certificate: {result.get('has_custom_certificate')}")
                print(f"   • Pending Update Count: {result.get('pending_update_count')}")
                if result.get('last_error_date'):
                    print(f"   ⚠️ Last Error Date: {result.get('last_error_date')}")
                    print(f"   ⚠️ Last Error Message: {result.get('last_error_message')}")
            else:
                print("   ⚠️ No webhook URL set.")
        else:
            print(f"❌ Failed to get webhook info: {webhook_info}")
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")

    print("\n🔹 Instructions:")
    print("1. Ensure your server is publicly accessible (e.g., via ngrok).")
    print("2. Your webhook URL should be: https://<your-domain>/api/v1/webhooks/telegram")
    print("3. To set the webhook, you can run:")
    print(f"   curl -F \"url=https://<your-domain>/api/v1/webhooks/telegram\" https://api.telegram.org/bot{token}/setWebhook")

if __name__ == "__main__":
    check_telegram_webhook()
