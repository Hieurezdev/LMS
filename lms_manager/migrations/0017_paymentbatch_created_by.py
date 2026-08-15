from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lms_manager", "0016_payment_payment_method"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentbatch",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="payment_batches",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Người tạo phiếu",
            ),
        ),
    ]
