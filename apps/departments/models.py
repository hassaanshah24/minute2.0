from django.db import models
from django.conf import settings  # Use AUTH_USER_MODEL for CustomUser reference

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Unique name of the department")
    description = models.TextField(blank=True, help_text="Optional description of the department")
    code = models.CharField(max_length=10, unique=True, help_text="A unique code for the department")
    head_of_department = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Reference CustomUser
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        help_text="User assigned as the Head of Department"
    )
    dean = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Reference CustomUser
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dean_departments',
        help_text="User assigned as the Dean of the Department"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_departments',
        help_text="User who created the department"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        constraints = [
            models.UniqueConstraint(
                fields=['head_of_department'],
                name='unique_head_of_department'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
