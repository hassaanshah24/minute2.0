# Generated by Django 5.1.4 on 2025-01-06 23:37

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_customuser_options_and_more"),
    ]

    operations = [
        # Removed `RemoveField` operation for "departments" since it doesn't exist in the database.
        migrations.AddField(
            model_name="customuser",
            name="profile_picture",
            field=models.ImageField(
                blank=True,
                help_text="User's profile picture.",
                null=True,
                upload_to="profile_pictures/",
            ),
        ),
    ]
