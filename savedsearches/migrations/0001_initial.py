from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedSearch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("query", models.JSONField(default=dict)),
                ("frequency", models.CharField(choices=[("instant", "Instant"), ("daily", "Daily")], default="daily", max_length=16)),
                ("is_active", models.BooleanField(default=True)),
                ("last_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_searches", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="savedsearch",
            index=models.Index(fields=["user", "is_active"], name="savedsearc_user_id__a4a102_idx"),
        ),
    ]

