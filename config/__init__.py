"""Django project package."""

# Best-effort Celery import: don't break runserver if Celery isn't installed yet.
try:  # pragma: no cover
    from .celery import app as celery_app  # noqa: F401
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore
