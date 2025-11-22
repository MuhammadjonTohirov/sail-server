from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import listings.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("taxonomy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Listing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("price_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("price_currency", models.CharField(default="UZS", max_length=3)),
                ("condition", models.CharField(choices=[("new", "New"), ("used", "Used")], default="used", max_length=16)),
                ("status", models.CharField(choices=[
                    ("draft", "Draft"),
                    ("pending_review", "Pending Review"),
                    ("active", "Active"),
                    ("paused", "Paused"),
                    ("closed", "Closed"),
                    ("expired", "Expired"),
                ], default="active", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("refreshed_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("quality_score", models.FloatField(default=0.0)),
                ("contact_phone_masked", models.CharField(blank=True, default="", max_length=32)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("lon", models.FloatField(blank=True, null=True)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="listings", to="taxonomy.category"),
                ),
                (
                    "location",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="listings", to="taxonomy.location"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="listings", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-refreshed_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ListingAttributeValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value_text", models.CharField(blank=True, default="", max_length=255)),
                ("value_number", models.FloatField(blank=True, null=True)),
                ("value_bool", models.BooleanField(blank=True, null=True)),
                ("value_option_key", models.CharField(blank=True, default="", max_length=64)),
                (
                    "attribute",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="taxonomy.attribute"),
                ),
                (
                    "listing",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attributes", to="listings.listing"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ListingMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(choices=[("photo", "Photo")], default="photo", max_length=10)),
                ("image", models.ImageField(upload_to=listings.models.listing_media_upload_to)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "listing",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media", to="listings.listing"),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["status", "category", "location", "refreshed_at"], name="listings_li_status__b5b46d_idx"),
        ),
        migrations.AddIndex(
            model_name="listingattributevalue",
            index=models.Index(fields=["listing"], name="listings_li_listing_5b89a7_idx"),
        ),
        migrations.AddIndex(
            model_name="listingattributevalue",
            index=models.Index(fields=["attribute"], name="listings_li_attribu_4c4225_idx"),
        ),
    ]

