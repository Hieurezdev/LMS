from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("lms_manager", "0022_payment_collected_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="collected_at",
            field=models.DateTimeField(
                blank=True,
                default=django.utils.timezone.now,
                editable=False,
                null=True,
                verbose_name="Giờ thu",
            ),
        ),
        migrations.AlterField(
            model_name="paymentbatch",
            name="created_at",
            field=models.DateTimeField(
                blank=True, default=django.utils.timezone.now, editable=False
            ),
        ),
    ]
