from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("listings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason_code", models.CharField(max_length=64)),
                ("notes", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved")], default="open", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "listing",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="listings.listing"),
                ),
                (
                    "reporter",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["status", "created_at"], name="moderation_status__b26e87_idx"),
        ),
    ]

