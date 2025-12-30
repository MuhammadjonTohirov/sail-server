from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_telegramchatconfig_chat_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="notify_new_messages",
            field=models.BooleanField(
                default=True, help_text="Notify about new chat messages"
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="notify_saved_searches",
            field=models.BooleanField(
                default=True, help_text="Notify about new items in saved searches"
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="notify_promotions",
            field=models.BooleanField(
                default=False, help_text="Notify about promotions and offers"
            ),
        ),
    ]
