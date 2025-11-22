# Generated migration for adding VILLAGE and QUARTER location kinds

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0007_allow_null_location_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='kind',
            field=models.CharField(
                choices=[
                    ('COUNTRY', 'Country'),
                    ('REGION', 'Region'),
                    ('DISTRICT', 'District'),
                    ('VILLAGE', 'Village'),
                    ('QUARTER', 'Quarter')
                ],
                max_length=16
            ),
        ),
    ]
