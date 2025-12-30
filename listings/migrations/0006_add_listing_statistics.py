from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0005_listing_contact_email_listing_contact_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='view_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='listing',
            name='interest_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
