from django.db import migrations, models


def approve_existing_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.update(is_approved=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_role")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_approved",
            field=models.BooleanField(default=False, verbose_name="Đã được duyệt"),
        ),
        migrations.RunPython(approve_existing_users, migrations.RunPython.noop),
    ]
