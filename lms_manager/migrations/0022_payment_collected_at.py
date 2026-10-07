from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lms_manager", "0021_paymentrequest_request_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="collected_at",
            field=models.DateTimeField(
                auto_now_add=True,
                blank=True,
                null=True,
                verbose_name="Giờ thu",
            ),
        ),
    ]
