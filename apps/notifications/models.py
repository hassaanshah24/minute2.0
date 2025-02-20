from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now, timedelta

User = get_user_model()

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user to whom the notification is addressed."
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the notification. Keep it short and concise."
    )
    message = models.TextField(
        help_text="Detailed message for the notification. Provide any necessary context."
    )
    link = models.URLField(
        blank=True,
        null=True,
        help_text="Optional link to provide additional context or a call-to-action."
    )
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='info',
        help_text="Type of notification to determine the priority and style."
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Indicates whether the notification has been read by the user."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the notification was created."
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Optional expiration time for the notification."
    )

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure notifications have a default expiry of 7 days
        if not explicitly set.
        """
        if not self.expires_at:
            self.expires_at = now() + timedelta(days=7)  # Default expiry: 7 days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.type}) - {self.user.username}"

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']  # Ensures notifications are ordered by the newest first
