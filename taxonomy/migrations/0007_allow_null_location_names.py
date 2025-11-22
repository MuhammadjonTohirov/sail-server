# Generated manually to allow NULL values in Location name_ru and name_uz fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0006_category_icon_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='name_ru',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='name_uz',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
