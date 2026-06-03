import os
from pathlib import Path

from dotenv import load_dotenv


# Load local environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Security: Default DEBUG to False for safety
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in {"1", "true", "yes"}

# Security: Require SECRET_KEY in production
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
if not DEBUG and SECRET_KEY == "dev-secret-key-change-me":
    raise ValueError("DJANGO_SECRET_KEY must be set in production!")

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
    if not ALLOWED_HOSTS:
        raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production!")

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
    # "uploads",
    "moderation",
    "chat",
    "currency",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # WhiteNoise qo'shildi
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

# Static files - WhiteNoise sozlamalari
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise static files storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS configuration (open in DEBUG for convenience)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    origins = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o]
    if not origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set in production!")
    CORS_ALLOWED_ORIGINS = origins
    
    # CSRF trusted origins mirror the allowed CORS origins
    CSRF_TRUSTED_ORIGINS = origins.copy()

# CORS credentials
CORS_ALLOW_CREDENTIALS = True

# Security headers for production
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in {"1", "true", "yes"}
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"

# DRF basics
_drf_auth_classes = [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]
# Only enable BasicAuth in DEBUG mode
if DEBUG:
    _drf_auth_classes.append("rest_framework.authentication.BasicAuthentication")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": tuple(_drf_auth_classes),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "config.api_response.ApiRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.api_response.ApiPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.api_response.api_exception_handler",
}

# Enable rate limiting in production
if not DEBUG:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = (
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    )
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "otp": "3/minute",
        "login": "5/minute",
        "auth": "10/minute",
        "anon": "100/hour",
    }

# OpenSearch
OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
OPENSEARCH_INDEX_PREFIX = os.environ.get("OPENSEARCH_INDEX_PREFIX", "sail")
OPENSEARCH_INDEX_VERSION = int(os.environ.get("OPENSEARCH_INDEX_VERSION", "2"))

# Celery (defaults are set in config/celery.py)
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "30"))
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "60"))

# Celery Beat schedule for periodic tasks
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    "daily-saved-search-notifications": {
        "task": "savedsearches.run_daily_notifications",
        "schedule": crontab(hour=9, minute=0),  # Run daily at 9:00 AM
        "options": {"expires": 3600},  # Expire after 1 hour if not picked up
    },
}

# SimpleJWT defaults can be overridden via env later if needed
# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "Sail API",
    "DESCRIPTION": (
        "Sail — C2C classifieds marketplace API.\n\n"
        "All responses follow a standard envelope:\n"
        "```json\n"
        '{ "success": true, "data": <payload>, "error": null, "code": 200 }\n'
        "```"
    ),
    "VERSION": "1.0.0",
    "CONTACT": {"name": "Sail Team"},
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    "TAGS": [
        {"name": "auth", "description": "Authentication (OTP, email/password, Telegram)"},
        {"name": "profile", "description": "User profile management"},
        {"name": "security", "description": "Password & account linking"},
        {"name": "listings", "description": "Listing CRUD & media"},
        {"name": "search", "description": "Full-text search with filters"},
        {"name": "chat", "description": "Chat threads & messages"},
        {"name": "favorites", "description": "Favorites & recently viewed"},
        {"name": "saved-searches", "description": "Saved search management"},
        {"name": "taxonomy", "description": "Categories, locations, attributes"},
        {"name": "moderation", "description": "Reporting & moderation queue"},
        {"name": "currency", "description": "Currency config & conversion"},
        {"name": "uploads", "description": "S3 presigned uploads"},
        {"name": "telegram", "description": "Telegram chat configs & webhooks"},
        {"name": "health", "description": "Health check & i18n"},
    ],
}

# Telegram integration (login + bot usage)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not DEBUG and not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in production!")
TELEGRAM_LOGIN_MAX_AGE = int(os.environ.get("TELEGRAM_LOGIN_MAX_AGE", "86400"))  # seconds (default 1 day)
TELEGRAM_WEBHOOK_SECRET_TOKEN = os.environ.get("TELEGRAM_WEBHOOK_SECRET_TOKEN", "")
WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "https://sail.uz")
# In production, set TELEGRAM_WEBHOOK_SECRET_TOKEN: openssl rand -hex 32

# ---------------------------------------------------------------------------
# Email delivery (OTP codes, password reset, registration verification)
# ---------------------------------------------------------------------------
# Backend selection:
#   - If EMAIL_HOST is configured -> SMTP backend (production).
#   - Else in DEBUG -> console backend (codes printed to stdout for local dev).
#   - Else (production with no EMAIL_HOST) -> SMTP backend with empty host,
#     which will raise loudly on send so misconfiguration is caught immediately
#     rather than silently dropping verification emails.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in {"1", "true", "yes"}
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in {"1", "true", "yes"}
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))

# Explicit backend override wins if provided; otherwise auto-select.
_email_backend_override = os.environ.get("EMAIL_BACKEND", "")
if _email_backend_override:
    EMAIL_BACKEND = _email_backend_override
elif EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    # Production without SMTP host configured: keep SMTP backend so sends fail
    # loudly (caught + logged in the OTP delivery service) instead of being
    # silently swallowed. Operators MUST set EMAIL_HOST in production.
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Sail <no-reply@sail.uz>")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
# Human-readable product name used in OTP email bodies.
EMAIL_PRODUCT_NAME = os.environ.get("EMAIL_PRODUCT_NAME", "Sail")

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