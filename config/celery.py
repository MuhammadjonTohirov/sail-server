import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("server")

# Broker config: prefer REDIS_URL or CELERY_BROKER_URL; fallback to memory:// for dev
broker_url = (
    os.environ.get("CELERY_BROKER_URL")
    or os.environ.get("REDIS_URL")
    or "memory://"
)
app.conf.broker_url = broker_url

# Run tasks eagerly in DEBUG if CELERY_TASK_ALWAYS_EAGER is set or no broker
task_always_eager_env = os.environ.get("CELERY_TASK_ALWAYS_EAGER")
if task_always_eager_env is not None:
    app.conf.task_always_eager = task_always_eager_env.lower() in {"1", "true", "yes"}
elif broker_url.startswith("memory://"):
    app.conf.task_always_eager = True

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

