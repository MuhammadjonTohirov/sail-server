from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taxonomy", "0003_rename_taxonomy_at_categor_6d5ae1_idx_taxonomy_at_categor_42e3d6_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="location",
            name="name_ru",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="location",
            name="name_uz",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="category",
            name="name_ru",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="category",
            name="name_uz",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="attribute",
            name="label_ru",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="attribute",
            name="label_uz",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
    ]

