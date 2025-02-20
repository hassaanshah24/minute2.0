from datetime import datetime
from django.db import models, transaction, connection
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.apps import apps
from django.db.models import Max, F
import os
import logging
logger = logging.getLogger(__name__)



# Dynamically fetch the custom user model
User = get_user_model()

def validate_file_extension(value):
    """
    Validate that the file has an allowed extension.
    """
    valid_extensions = ['.png', '.jpeg', '.jpg', '.pdf']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f"Unsupported file extension: {ext}. Allowed extensions: {', '.join(valid_extensions)}")


def validate_file_size(value):
    """
    Validate that the file size does not exceed 10MB.
    """
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError("File size exceeds 10MB limit.")


class Minute(models.Model):
    """
    Represents a document that goes through an approval workflow.
    """
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Submitted', 'Submitted'),
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Marked', 'Marked'),
        ('Returned', 'Returned'),
    ]

    title = models.CharField(max_length=255, help_text="Title of the minute.")
    subject = models.TextField(
        help_text="Subject of the minute sheet.",
        blank=True,  # Allow empty input
        default=""
    )

    description = models.TextField(help_text="Detailed description of the minute.")
    attachment = models.FileField(
        upload_to='minutes/',
        blank=True,
        null=True,
        validators=[validate_file_extension, validate_file_size],
        help_text="Optional file attachment for the minute."
    )
    sheet_number = models.PositiveIntegerField(
        help_text="Sheet number for multi-page minute sheets.",
        default=1
    )
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="minutes",
        help_text="The department this minute sheet belongs to."
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='minutes',
        help_text="The user who created this minute."
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the minute was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of the last update.")
    unique_id = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
        help_text="Auto-generated unique ID for the minute."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Draft',
        help_text="Current status of the minute."
    )
    approval_chain = models.OneToOneField(
        'approval_chain.ApprovalChain',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='linked_minute',
        help_text="Links the minute to its unique approval chain."
    )
    archived = models.BooleanField(
        default=False,
        help_text="Marks the minute as archived after final approval."
    )

    def archive(self, status):
        """
        Archive the minute by setting its status to 'Approved' or 'Rejected'.
        Ensures that archived=True is explicitly set.
        """
        if status not in ['Approved', 'Rejected']:
            raise ValueError("Invalid status for archiving. Use 'Approved' or 'Rejected'.")

        self.status = status
        self.archived = True  # ✅ Explicitly mark as archived
        self.updated_at = now()
        self.save()

    def _get_next_id(self):
        """
        Safely fetch the next available ID by querying the database.
        """
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM minute_minute;")
            next_id = cursor.fetchone()[0]
        return next_id

    def _generate_unique_id(self):
        """
        Generates a university-standard minute sheet ID:
        Format: DHA/DSU/<Department_Code>/<MM-YYYY>/<####>
        Example: DHA/DSU/CS/02-2025/0012
        """
        month_year = datetime.now().strftime("%m-%Y")
        unique_number = str(self.pk or self._get_next_id()).zfill(4)

        # Get department code properly
        department_code = self.department.code if self.department else "GEN"

        return f"DHA/DSU/{department_code}/{month_year}/{unique_number}"

    def save(self, *args, **kwargs):
        """
        Override save to ensure unique ID and handle sequence misalignment.
        Auto-create MinuteApproval records when linked to an ApprovalChain.
        """
        is_new = self.pk is None

        # Ensure unique_id is generated correctly
        if is_new:
            self.pk = self._get_next_id()

        if not self.unique_id:
            self.unique_id = self._generate_unique_id()

        # Prevent submission without an approval chain
        if self.status == 'Submitted' and not self.approval_chain:
            raise ValidationError("A Minute must be linked to an approval chain before submission.")

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Override delete to explicitly delete related ApprovalChain.
        """
        if self.approval_chain:
            self.approval_chain.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.unique_id})"

# Remaining part for `MinuteApproval` remains as previously corrected.

class MinuteApproval(models.Model):
    """
    Tracks the approval process for each approver in the chain.
    """
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('mark-to', 'Mark-To'),
        ('return-to', 'Return-To'),
    ]

    minute = models.ForeignKey(
        'minute.Minute',
        on_delete=models.CASCADE,
        related_name="approvals",
        help_text="The minute document being tracked for approval."
    )
    approval_chain = models.ForeignKey(
        'approval_chain.ApprovalChain',
        on_delete=models.CASCADE,
        related_name="minute_approvals",
        help_text="The approval chain linked to this minute."
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="approvals",
        help_text="The user responsible for reviewing the minute."
    )
    current_approver = models.BooleanField(
        default=False,
        help_text="Indicates if the user is the current approver in the chain."
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        null=True,
        blank=True,
        help_text="Action performed by the approver."
    )
    remarks = models.TextField(
        null=True,
        blank=True,
        help_text="Optional remarks provided by the approver."
    )
    target_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='marked_minutes',
        help_text="The user to whom this minute is marked (for mark-to action)."
    )
    action_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of when the approver performed the action."
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
            ('Marked', 'Marked'),
            ('Returned', 'Returned'),
        ],
        default='Pending',
        help_text="Tracks the current status of the approval process."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the approval record was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the approval record was last updated."
    )

    order = models.PositiveIntegerField(
        null=False,
        blank=False,
        help_text="Sequence/order of this approver in the approval chain."
    )

    class Meta:
        unique_together = ('minute', 'approver')
        constraints = [
            models.UniqueConstraint(
                fields=['minute'],
                condition=models.Q(current_approver=True),
                name='unique_current_approver_per_minute'
            )
        ]
        verbose_name = "Minute Approval"
        verbose_name_plural = "Minute Approvals"

    def __str__(self):
        return f"{self.minute.title} - {self.status} by {self.approver.username}"

    # Core business logic methods

    @transaction.atomic
    def approve(self, remarks=None):
        from apps.approval_chain.models import Approver

        logger.debug(f"Approving with remarks: {remarks}")

        # Default remarks if none provided
        if not remarks:
            remarks = "Approved without remarks"

        # Update the approval instance
        self.status = 'Approved'
        self.action = 'approve'
        self.remarks = remarks
        self.action_time = now()
        self.current_approver = False
        self.save()

        logger.info(f"Approval saved: ID={self.id}, Status={self.status}")

        # Log the approval action
        MinuteActionLog.objects.create(
            minute=self.minute,
            action='approve',
            performed_by=self.approver,
            remarks=remarks or f"Approved by {self.approver.get_full_name()}"
        )

        # Update the approver entry
        approver_entry = Approver.objects.get(approval_chain=self.approval_chain, user=self.approver)
        approver_entry.status = 'Approved'
        approver_entry.is_current = False
        approver_entry.save(update_fields=['status', 'is_current'])

        # Assign the next approver
        next_approver = self.approval_chain.get_next_approver(current_order=approver_entry.order)
        if next_approver:
            next_approval, created = MinuteApproval.objects.get_or_create(
                minute=self.minute,
                approver=next_approver.user,
                defaults={
                    'approval_chain': self.approval_chain,
                    'current_approver': True,
                    'status': 'Pending',
                    'order': next_approver.order
                }
            )
            next_approval.current_approver = True
            next_approval.save(update_fields=['current_approver'])
            next_approver.is_current = True
            next_approver.save(update_fields=['is_current'])
            logger.info(f"Next approver assigned: User={next_approver.user.username}, Order={next_approver.order}")
        else:
            # ✅ Final approver - Archive the minute
            self.minute.archive('Approved')
            logger.info(f"Minute archived: ID={self.minute.id}, Status=Approved")

    @transaction.atomic
    def reject(self, remarks=None):
        from apps.approval_chain.models import Approver

        if not remarks:
            remarks = "Rejected without remarks"

        self.status = 'Rejected'
        self.action = 'reject'
        self.remarks = remarks
        self.action_time = now()
        self.current_approver = False
        self.save()
        logger.info(f"Rejection saved: ID={self.id}, Remarks={self.remarks}")

        MinuteActionLog.objects.create(
            minute=self.minute,
            action='reject',
            performed_by=self.approver,
            remarks=remarks
        )

        approver_entry = Approver.objects.get(approval_chain=self.approval_chain, user=self.approver)
        approver_entry.status = 'Rejected'
        approver_entry.is_current = False
        approver_entry.save(update_fields=['status', 'is_current'])

        # ✅ Archive the minute when rejected
        self.minute.archive('Rejected')
        logger.info(f"Minute archived: ID={self.minute.id}, Status=Rejected")

    @transaction.atomic
    def mark_to(self, target_user, order=None):
        from django.apps import apps
        Approver = apps.get_model('approval_chain', 'Approver')

        # Validate the target user
        self._validate_target_user(target_user)

        # Update the current approver's MinuteApproval record
        self._update_status('Marked', 'mark-to', target_user=target_user)

        # Determine the new approver's order
        current_order = Approver.objects.get(approval_chain=self.approval_chain, user=self.approver).order
        new_order = order if order is not None else current_order + 1

        # Adjust orders of existing approvers to make space for the new approver
        Approver.objects.filter(
            approval_chain=self.approval_chain,
            order__gte=new_order
        ).update(order=F('order') + 1)

        # Add the new approver to the ApprovalChain
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=new_order,
            status='Pending',
            is_current=True
        )

        # Create a corresponding MinuteApproval record for the new approver
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.create(
            minute=self.minute,
            approval_chain=self.approval_chain,
            approver=new_approver.user,
            order=new_approver.order,
            status='Pending',
            current_approver=True
        )
        logger.info(f"Minute marked to new approver: User={new_approver.user.username}, Order={new_approver.order}")

    @transaction.atomic
    def return_to(self, target_user):
        from django.apps import apps
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        Approver = apps.get_model('approval_chain', 'Approver')

        self._validate_target_user(target_user, for_return=True)

        self._update_status('Returned', 'return-to', target_user=target_user)

        returned_approval = MinuteApproval.objects.filter(
            minute=self.minute,
            approver=target_user
        ).first()

        if not returned_approval:
            raise ValidationError(f"{target_user.username} has no valid MinuteApproval record for this minute.")

        returned_approval.status = 'Pending'
        returned_approval.current_approver = True
        returned_approval.save(update_fields=['status', 'current_approver'])

        approver_entry = Approver.objects.get(approval_chain=self.approval_chain, user=target_user)
        approver_entry.status = 'Pending'
        approver_entry.is_current = True
        approver_entry.save(update_fields=['status', 'is_current'])

        MinuteActionLog.objects.create(
            minute=self.minute,
            action='return-to',
            performed_by=self.approver,
            target_user=target_user,
            remarks=f"Returned to {target_user.get_full_name()} by {self.approver.get_full_name()}"
        )

        self.minute.status = 'Pending'  # Explicitly set to Pending
        self.minute.save(update_fields=['status'])
        logger.info(f"Minute returned to: User={target_user.username}")

    # Helper Methods

    def _update_status(self, status, action, target_user=None):
        """
        Updates the status, action, and logs the change.
        """
        self.status = status
        self.action = action
        self.target_user = target_user
        self.action_time = now()
        self.current_approver = False
        self.save()

        # Log the action in the MinuteActionLog
        MinuteActionLog.objects.create(
            minute=self.minute,
            action=action,
            performed_by=self.approver,
            target_user=target_user,
            remarks=f"{action.capitalize()} action performed by {self.approver.get_full_name()}"
        )

    def _finalize_minute(self, status):
        """
        Finalize the minute with the given status.
        """
        self.minute.status = status
        self.minute.save(update_fields=['status'])
        self.approval_chain.check_and_update_status()

    def _get_current_order(self):
        """
        Retrieve the current order of the approver.
        """
        from django.apps import apps

        # Use dynamic imports to avoid circular import issues
        Approver = apps.get_model('approval_chain', 'Approver')
        return Approver.objects.get(approval_chain=self.approval_chain, user=self.approver).order

    def _set_as_current(self, next_approver):
        """
        Sets the next approver as the current active approver.
        """
        from django.apps import apps

        # Use dynamic imports to avoid circular import issues
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.filter(
            minute=self.minute, approver=next_approver.user
        ).update(current_approver=True, status='Pending')

    def _get_next_approver(self):
        """
        Retrieve the next approver in the chain.
        """
        from django.apps import apps

        # Use dynamic imports to avoid circular import issues
        Approver = apps.get_model('approval_chain', 'Approver')

        current_order = Approver.objects.get(
            approval_chain=self.approval_chain,
            user=self.approver
        ).order

        return Approver.objects.filter(
            approval_chain=self.approval_chain,
            order__gt=current_order
        ).order_by('order').first()

    def _validate_target_user(self, target_user, for_return=False):
        """
        Validate the target user for mark-to or return-to actions.
        """
        if for_return:
            returned_approval = MinuteApproval.objects.filter(
                minute=self.minute, approver=target_user
            ).first()
            if not returned_approval:
                raise ValidationError(f"User {target_user.username} has no valid approval record.")

        else:
            if self.approval_chain.approvers.filter(user=target_user).exists():
                raise ValidationError(f"User {target_user.username} is already in the approval chain.")

    @classmethod
    def get_current_approval_status(cls, minute):
        """
        Retrieve the current approval status of all approvers for a given minute.
        """
        return cls.objects.filter(minute=minute).values('approver__username', 'status', 'current_approver')

    @classmethod
    def get_all_approvals(cls, minute):
        """
        Retrieve detailed information about all approvals for a given minute.
        """
        return cls.objects.filter(minute=minute).values(
            'approver__username',
            'status',
            'current_approver',
            'action',
            'remarks',
            'action_time'
        )


class MinuteActionLog(models.Model):
    """
    Logs every action taken on a Minute during its approval process.
    """
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('mark-to', 'Mark-To'),
        ('return-to', 'Return-To'),
    ]

    minute = models.ForeignKey(
        Minute,
        on_delete=models.CASCADE,
        related_name="action_logs",
        help_text="The minute document related to this log entry."
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="The action performed on the minute."
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_actions",
        help_text="The user who performed the action."
    )
    target_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="targeted_actions",
        help_text="The target user for the action, if applicable (e.g., Mark-To, Return-To)."
    )
    remarks = models.TextField(
        null=True,
        blank=True,
        help_text="Optional remarks or comments associated with the action."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="The time when the action was performed."
    )

    def log_action(self, action, remarks=None, target_user=None, timestamp=None):
        """
        Log an action with optional remarks, target user, and custom timestamp.
        """
        if action in ['mark-to', 'return-to'] and not target_user:
            raise ValidationError(f"Target user is required for action '{action}'.")

        MinuteActionLog.objects.create(
            minute=self.minute,
            action=action,
            performed_by=self.approver,
            target_user=target_user,
            remarks=remarks or '',
            timestamp=timestamp or now()
        )

    @classmethod
    def get_logs_for_minute(cls, minute):
        """
        Retrieve all logs for a given minute, ordered by timestamp.
        """
        return cls.objects.filter(minute=minute).order_by('timestamp')

    class Meta:
        indexes = [
            models.Index(fields=['action'], name='action_idx'),
            models.Index(fields=['timestamp'], name='timestamp_idx'),
        ]
        verbose_name = "Minute Action Log"
        verbose_name_plural = "Minute Action Logs"

    def __str__(self):
        return f"{self.action.capitalize()} on {self.minute.title} by {self.performed_by.username if self.performed_by else 'System'}"

