# Generated migration for adding listing availability tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatthread',
            name='listing_availability',
            field=models.CharField(
                choices=[
                    ('available', 'Available'),
                    ('unavailable', 'Unavailable'),
                    ('deleted', 'Deleted')
                ],
                default='available',
                help_text='Cached availability status of the listing',
                max_length=16
            ),
        ),
        migrations.AddField(
            model_name='chatthread',
            name='listing_availability_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
