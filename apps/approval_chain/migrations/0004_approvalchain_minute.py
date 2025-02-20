# Generated by Django 5.1.4 on 2025-01-13 09:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("approval_chain", "0003_alter_approver_status"),
        ("minute", "0005_minute_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalchain",
            name="minute",
            field=models.OneToOneField(
                default=1,
                help_text="The minute document linked to this approval chain.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="linked_approval_chain",
                to="minute.minute",
            ),
            preserve_default=False,
        ),
    ]
