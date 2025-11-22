from django.apps import AppConfig


class ListingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "listings"

    def ready(self):  # pragma: no cover
        from . import signals  # noqa: F401
