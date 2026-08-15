# Generated manually to remove student contact data at the application's request.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lms_manager', '0017_paymentbatch_created_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='phone',
        ),
    ]
