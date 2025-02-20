# Generated by Django 5.1.4 on 2025-01-07 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "notifications",
            "0003_notification_category_notification_expires_at_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notification",
            name="category",
        ),
        migrations.AddField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("info", "Info"),
                    ("success", "Success"),
                    ("warning", "Warning"),
                    ("error", "Error"),
                ],
                default="info",
                help_text="Type of notification.",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="Timestamp when the notification was created.",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="is_read",
            field=models.BooleanField(
                default=False, help_text="Whether the notification has been read."
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="link",
            field=models.URLField(
                blank=True, help_text="Optional link for the notification.", null=True
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="message",
            field=models.TextField(help_text="Detailed message for the notification."),
        ),
        migrations.AlterField(
            model_name="notification",
            name="title",
            field=models.CharField(
                help_text="Title of the notification.", max_length=255
            ),
        ),
    ]
