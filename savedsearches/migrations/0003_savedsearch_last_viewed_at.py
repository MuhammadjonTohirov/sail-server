# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('savedsearches', '0002_rename_savedsearc_user_id__a4a102_idx_savedsearch_user_id_56e988_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedsearch',
            name='last_viewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
