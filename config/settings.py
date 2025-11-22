import os
from pathlib import Path

from dotenv import load_dotenv


# Load local environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h] or []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "health",
    "taxonomy",
    "accounts",
    "listings",
    "searchapp",
    "savedsearches",
    "favorites",
    "uploads",
    "moderation",
    "chat",
    "currency",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database: default to SQLite for local dev; switch to Postgres via env
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "sail"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 20,  # Increase timeout for locked database
            },
        }
    }
    # Enable WAL mode for better concurrency with SQLite
    import sqlite3
    from django.db.backends.signals import connection_created
    from django.dispatch import receiver

    @receiver(connection_created)
    def enable_sqlite_wal_mode(sender, connection, **kwargs):
        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA busy_timeout=20000;')  # 20 seconds

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "ru")
LANGUAGES = (
    ("ru", "Russian"),
    ("uz", "Uzbek"),
)
LOCALE_PATHS = [BASE_DIR / "locale"]
# Set to Uzbekistan time as a sensible default for this project
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS configuration (open in DEBUG for convenience)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    origins = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o]
    CORS_ALLOWED_ORIGINS = origins

# DRF basics
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Throttling disabled for development
    # "DEFAULT_THROTTLE_CLASSES": (
    #     "rest_framework.throttling.ScopedRateThrottle",
    #     "rest_framework.throttling.UserRateThrottle",
    #     "rest_framework.throttling.AnonRateThrottle",
    # ),
    # "DEFAULT_THROTTLE_RATES": {
    #     "otp": "5/minute",
    #     "user": "1000/day",
    #     "anon": "200/day",
    # },
}

# OpenSearch
OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
OPENSEARCH_INDEX_PREFIX = os.environ.get("OPENSEARCH_INDEX_PREFIX", "olxclone")
OPENSEARCH_INDEX_VERSION = int(os.environ.get("OPENSEARCH_INDEX_VERSION", "2"))

# Celery (defaults are set in config/celery.py)
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "30"))
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "60"))

# SimpleJWT defaults can be overridden via env later if needed
# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "OLX Clone API",
    "DESCRIPTION": "Classifieds platform API",
    "VERSION": "1.0.0",
}

# Telegram integration (login + bot usage)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8314735056:AAEQSsb7cgR-VR4U6rPZ8z_pHLUViH2asc8")
TELEGRAM_LOGIN_MAX_AGE = int(os.environ.get("TELEGRAM_LOGIN_MAX_AGE", "86400"))  # seconds (default 1 day)

# Logging (basic)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"}
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Chat feature toggles
CHAT_MAX_ATTACHMENTS_PER_MESSAGE = int(os.environ.get("CHAT_MAX_ATTACHMENTS_PER_MESSAGE", "5"))
_chat_attachment_prefixes = [
    p.strip()
    for p in os.environ.get("CHAT_ATTACHMENT_ALLOWED_URL_PREFIXES", "").split(",")
    if p.strip()
]
if not _chat_attachment_prefixes:
    media_url = str(MEDIA_URL)
    if media_url.startswith(("http://", "https://")):
        _chat_attachment_prefixes.append(media_url)
CHAT_ATTACHMENT_ALLOWED_URL_PREFIXES = _chat_attachment_prefixes
