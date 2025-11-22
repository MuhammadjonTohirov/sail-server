# Generated migration for Profile settings fields

import accounts.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('taxonomy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to=accounts.models.profile_banner_upload_to),
        ),
        migrations.AddField(
            model_name='profile',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_profiles', to='taxonomy.location'),
        ),
        migrations.AddField(
            model_name='profile',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to=accounts.models.profile_logo_upload_to),
        ),
    ]
