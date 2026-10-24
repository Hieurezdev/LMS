from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lms_manager', '0024_student_start_period'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name=f'attends_period_{number}',
            field=models.BooleanField(blank=True, default=None, null=True),
        )
        for number in range(1, 9)
    ]
