# Generated by Django 5.1.4 on 2025-01-06 21:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Unique name of the department",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Optional description of the department"
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="A unique code for the department",
                        max_length=10,
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_departments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "head_of_department",
                    models.ForeignKey(
                        blank=True,
                        help_text="User assigned as the Head of Department",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="headed_departments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
