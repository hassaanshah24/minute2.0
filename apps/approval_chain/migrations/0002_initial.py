# Generated by Django 5.1.4 on 2025-01-06 21:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("approval_chain", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalchain",
            name="created_by",
            field=models.ForeignKey(
                help_text="The user who created this approval chain.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_chains",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="approver",
            name="approval_chain",
            field=models.ForeignKey(
                help_text="The approval chain this approver belongs to.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="approvers",
                to="approval_chain.approvalchain",
            ),
        ),
        migrations.AddField(
            model_name="approver",
            name="user",
            field=models.ForeignKey(
                help_text="The user assigned as an approver.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="approval_roles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="approver",
            unique_together={("approval_chain", "order")},
        ),
    ]
