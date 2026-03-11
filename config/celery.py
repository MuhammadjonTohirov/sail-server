import os
import warnings

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("server")

# Check if we're in DEBUG mode
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in {"1", "true", "yes"}

# Broker config: prefer REDIS_URL or CELERY_BROKER_URL; fallback to memory:// only in DEBUG
broker_url = (
    os.environ.get("CELERY_BROKER_URL")
    or os.environ.get("REDIS_URL")
)

if not broker_url:
    if DEBUG:
        # Allow memory broker in development
        broker_url = "memory://"
        warnings.warn(
            "Using in-memory Celery broker. Tasks will be lost on restart. "
            "Set REDIS_URL or CELERY_BROKER_URL for persistent task queue.",
            RuntimeWarning,
        )
    else:
        raise ValueError(
            "CELERY_BROKER_URL or REDIS_URL must be set in production! "
            "Tasks cannot use memory:// broker in production."
        )

app.conf.broker_url = broker_url

# Run tasks eagerly in DEBUG if CELERY_TASK_ALWAYS_EAGER is set or using memory broker
task_always_eager_env = os.environ.get("CELERY_TASK_ALWAYS_EAGER")
if task_always_eager_env is not None:
    app.conf.task_always_eager = task_always_eager_env.lower() in {"1", "true", "yes"}
elif broker_url.startswith("memory://"):
    app.conf.task_always_eager = True

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

