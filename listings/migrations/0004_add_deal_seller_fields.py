from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_rename_listings_li_status__b5b46d_idx_listings_li_status_c7f971_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="deal_type",
            field=models.CharField(
                choices=[("sell", "Sell"), ("exchange", "Exchange"), ("free", "Free")],
                default="sell",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="seller_type",
            field=models.CharField(
                choices=[("person", "Person"), ("business", "Business")],
                default="person",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="is_price_negotiable",
            field=models.BooleanField(default=False),
        ),
    ]
