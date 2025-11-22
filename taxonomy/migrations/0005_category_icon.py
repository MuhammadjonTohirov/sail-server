from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taxonomy", "0004_i18n_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="icon",
            field=models.CharField(max_length=64, blank=True, default=""),
        ),
    ]

