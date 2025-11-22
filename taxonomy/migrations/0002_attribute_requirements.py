from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taxonomy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="attribute",
            name="is_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="attribute",
            name="min_number",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attribute",
            name="max_number",
            field=models.FloatField(blank=True, null=True),
        ),
    ]

