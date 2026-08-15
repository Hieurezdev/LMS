from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("admin", "Quản trị viên"), ("cashier", "Thu ngân")],
                default="cashier",
                max_length=20,
            ),
        ),
    ]
