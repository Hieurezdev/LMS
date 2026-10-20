from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lms_manager', '0023_payment_collection_timestamp_defaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='start_period',
            field=models.PositiveSmallIntegerField(
                choices=[(number, f'Đợt {number}') for number in range(1, 9)],
                default=1,
                verbose_name='Bắt đầu thu học phí từ đợt',
            ),
        ),
    ]
