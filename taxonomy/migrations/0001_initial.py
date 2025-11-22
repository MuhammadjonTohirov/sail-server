from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("COUNTRY", "Country"), ("REGION", "Region"), ("CITY", "City"), ("DISTRICT", "District")], max_length=16)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("lon", models.FloatField(blank=True, null=True)),
                (
                    "parent",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="taxonomy.location"),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.PositiveSmallIntegerField(default=0)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("is_leaf", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "parent",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="taxonomy.category"),
                ),
            ],
            options={"ordering": ["order", "name"]},
        ),
        migrations.CreateModel(
            name="Attribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=255)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("number", "Number"),
                            ("boolean", "Boolean"),
                            ("select", "Select"),
                            ("multiselect", "Multiselect"),
                            ("range", "Range"),
                        ],
                        max_length=16,
                    ),
                ),
                ("unit", models.CharField(blank=True, max_length=32, null=True)),
                ("options", models.JSONField(blank=True, default=list)),
                ("is_indexed", models.BooleanField(default=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attributes", to="taxonomy.category")),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.AddIndex(model_name="location", index=models.Index(fields=["parent"], name="taxonomy_lo_parent__bcb28a_idx")),
        migrations.AddIndex(model_name="category", index=models.Index(fields=["parent"], name="taxonomy_ca_parent__e5bfe2_idx")),
        migrations.AddIndex(model_name="category", index=models.Index(fields=["order"], name="taxonomy_ca_order_5ddc7c_idx")),
        migrations.AlterUniqueTogether(name="attribute", unique_together={("category", "key")}),
        migrations.AddIndex(model_name="attribute", index=models.Index(fields=["category", "key"], name="taxonomy_at_categor_6d5ae1_idx")),
    ]

