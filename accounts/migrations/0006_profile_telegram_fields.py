from django.db import migrations, models


class Migration(migrations.Migration):

  dependencies = [
      ("accounts", "0005_otpcode_email_otpcode_purpose_and_more"),
  ]

  operations = [
      migrations.AddField(
          model_name="profile",
          name="telegram_id",
          field=models.BigIntegerField(blank=True, null=True, unique=True),
      ),
      migrations.AddField(
          model_name="profile",
          name="telegram_username",
          field=models.CharField(blank=True, default="", max_length=255),
      ),
      migrations.AddField(
          model_name="profile",
          name="telegram_photo_url",
          field=models.URLField(blank=True, default=""),
      ),
  ]
