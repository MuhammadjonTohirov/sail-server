from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taxonomy", "0005_category_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="icon_image",
            field=models.ImageField(blank=True, null=True, upload_to="category_icons/"),
        ),
    ]
