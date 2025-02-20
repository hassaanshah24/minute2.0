from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('Faculty', 'Faculty'),
        ('Admin', 'Admin'),
        ('Superuser', 'Superuser'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Role of the user in the system."
    )
    department = models.ForeignKey(
        'departments.Department',  # Avoid circular imports
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Department to which the user belongs."
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text="Unique Employee ID (can be set or updated later)."
    )
    designation = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="User's designation in the organization."
    )
    phone_number = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text="Contact phone number for the user."
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True, blank=True,
        help_text="User's profile picture."
    )

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'role'],
                name='unique_username_role'
            )
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"

    def clean(self):
        """
        Ensure the employee_id is unique if provided, and handle empty department values.
        """
        if self.employee_id:
            existing_user = CustomUser.objects.filter(employee_id=self.employee_id).exclude(pk=self.pk).first()
            if existing_user:
                raise ValidationError({"employee_id": "This Employee ID is already in use."})

        # Handle empty strings for department
        if self.department == '':
            self.department = None
