from django.apps import apps
from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.db import transaction
from django.db.models import Max, F
from django.core.exceptions import ValidationError

from apps.minute.models import MinuteApproval


class ApprovalChain(models.Model):
    """
    Represents an approval chain linked to a specific minute.
    Tracks the sequence of approvers and the overall approval status.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="A unique name for the approval chain."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_chains",
        help_text="The user who created this approval chain."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The timestamp when this chain was created."
    )
    status = models.CharField(
        max_length=20,
        choices=[('Active', 'Active'), ('Completed', 'Completed')],
        default='Active',
        help_text="The current status of the approval chain."
    )
    minute = models.OneToOneField(
        'minute.Minute',  # Reference the model by its app and model name as a string
        on_delete=models.CASCADE,
        related_name='linked_approval_chain',
        null=True,
        blank=True,
        help_text="The minute document linked to this approval chain."
    )

    class Meta:
        verbose_name = "Approval Chain"
        verbose_name_plural = "Approval Chains"

    def __str__(self):
        return self.name

    def get_next_approver(self, current_order=None):
        """
        Retrieve the next approver in sequence.
        """
        approvers = self.approvers.filter(status='Pending').order_by('order')
        if current_order is not None:
            approvers = approvers.filter(order__gt=current_order)
        return approvers.first()  # Returns None if no next approver exists

    @transaction.atomic
    def complete_chain(self, approved=True):
        """
        Marks the chain as completed and updates the associated minute's status.
        """
        self.status = 'Completed'
        self.save(update_fields=['status'])

        # Update the linked Minute's status
        self.minute.status = 'Approved' if approved else 'Rejected'
        self.minute.save(update_fields=['status'])

    @transaction.atomic
    def check_and_update_status(self):
        """
        Checks if all approvals are completed and updates the chain status.
        """
        if not self.minute_approvals.filter(status='Pending').exists():
            self.status = 'Completed'
            self.save(update_fields=['status'])

    @transaction.atomic
    def add_approver(self, user, order):
        """
        Adds a new approver to the chain at the specified order.
        """
        # Validate input
        max_order = self.approvers.aggregate(Max('order'))['order__max'] or 0
        if order < 1 or order > max_order + 1:
            raise ValidationError(f"Invalid order. Must be between 1 and {max_order + 1}.")

        if self.approvers.filter(user=user).exists():
            raise ValidationError(f"{user.username} is already an approver in this chain.")

        # Adjust existing approvers' orders
        self.approvers.filter(order__gte=order).update(order=F('order') + 1)

        # Add new approver
        return Approver.objects.create(
            approval_chain=self,
            user=user,
            order=order,
            status='Pending'
        )

    @transaction.atomic
    def reorder_approvals(self):
        """
        Reorder all approvers and their MinuteApproval records to ensure consistency.
        """
        approvers = self.approvers.order_by('order')
        for idx, approver in enumerate(approvers, start=1):
            approver.order = idx
            approver.save(update_fields=['order'])

            MinuteApproval.objects.filter(
                approval_chain=self,
                approver=approver.user
            ).update(order=idx)



class Approver(models.Model):
    """
    Represents individual approvers in an approval chain.
    Handles workflow actions like approve, reject, mark-to, and return-to.
    """
    approval_chain = models.ForeignKey(
        'approval_chain.ApprovalChain',
        on_delete=models.CASCADE,
        related_name="approvers",
        help_text="The approval chain this approver belongs to."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_roles",
        help_text="The user assigned as an approver."
    )
    order = models.PositiveIntegerField(
        help_text="The sequence/order of this approver in the chain. Starts from 1."
    )
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Marked', 'Marked'),
        ('Returned', 'Returned'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        help_text="The current status of this approver's action."
    )
    action_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The timestamp when this approver took action."
    )
    is_current = models.BooleanField(
        default=False,
        help_text="Indicates if this approver is the current active approver."
    )

    class Meta:
        unique_together = ('approval_chain', 'order')  # Ensure no duplicate orders in a chain
        ordering = ['order']
        verbose_name = "Approver"
        verbose_name_plural = "Approvers"

    def __str__(self):
        return f"{self.user.username} - {self.approval_chain.name} (Order: {self.order})"

    # Transactional Actions
    @transaction.atomic
    def approve(self):
        """
        Approves the current minute and progresses to the next approver.
        """
        self._update_status('Approved')
        next_approver = self.approval_chain.get_next_approver(current_order=self.order)
        if next_approver:
            next_approver._set_as_current()
        else:
            self.approval_chain.complete_chain(approved=True)

    @transaction.atomic
    def reject(self):
        """
        Rejects the minute and terminates the approval process for the entire chain.
        Also updates the status of all subsequent approvers to 'Rejected'.
        """
        # Update this approver's status to 'Rejected'
        self._update_status('Rejected')

        # Reject all subsequent approvers in the chain
        subsequent_approvers = self.approval_chain.approvers.filter(order__gt=self.order, status='Pending')
        subsequent_approvers.update(status='Rejected', is_current=False)

        # Dynamically fetch the MinuteApproval model and update their records
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.filter(
            minute=self.approval_chain.minute,
            approver__in=subsequent_approvers.values_list('user', flat=True)
        ).update(status='Rejected', current_approver=False)

        # Mark the entire minute as rejected
        self.approval_chain.complete_chain(approved=False)

    @transaction.atomic
    def mark_to(self, user, order=None):
        """
        Marks the minute to another user, adding them to the approval chain.
        Adjusts orders and sets the new approver as the current approver.
        """
        # Default to placing the new approver immediately after the current one if no order is provided
        if order is None:
            order = self.order + 1

        # Validate order range
        max_order = self.approval_chain.approvers.aggregate(Max('order'))['order__max'] or 0
        if order < 1 or order > max_order + 1:
            raise ValidationError(f"Invalid order: {order}. Must be between 1 and {max_order + 1}.")

        # Ensure the user is not already an approver
        if self.approval_chain.approvers.filter(user=user).exists():
            raise ValidationError(f"User {user.username} is already in the approval chain.")

        # Adjust orders of existing approvers
        self.approval_chain.approvers.filter(order__gte=order).update(order=F('order') + 1)

        # Add the new approver
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=user,
            order=order,
            status='Pending',
            is_current=True
        )

        # Update current approver's status
        self._update_status('Marked')

        # Sync with MinuteApproval
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.create(
            minute=self.approval_chain.minute,
            approval_chain=self.approval_chain,
            approver=user,
            status='Pending',
            current_approver=True
        )

        return new_approver

    @transaction.atomic
    def reorder_approvers(self):
        """
        Reorders all approvers in the chain to ensure sequential order.
        """
        approvers = self.approval_chain.approvers.order_by('order')
        for idx, approver in enumerate(approvers, start=1):
            if approver.order != idx:
                approver.order = idx
                approver.save(update_fields=['order'])

    @transaction.atomic
    def return_to(self, approver):
        """
        Returns the minute to a previous approver.
        """
        if approver.order >= self.order:
            raise ValidationError("Cannot return to an approver with the same or higher order.")

        # Update current approver's status
        self._update_status('Returned')

        # Set the target approver as current
        approver._set_as_current()

    # Utility Methods
    def _update_status(self, status):
        """
        Updates the status and action time of the approver.
        """
        self.status = status
        self.action_time = now()
        self.is_current = False
        self.save()

        # Update MinuteApproval record
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.filter(minute=self.approval_chain.minute, approver=self.user).update(
            status=status, current_approver=False, action_time=self.action_time
        )

    def _progress_to_next_approver(self):
        """
        Activates the next approver in the chain or completes the approval process.
        """
        next_approver = self.approval_chain.get_next_approver(current_order=self.order)
        if next_approver:
            next_approver._set_as_current()
        else:
            self.approval_chain.complete_chain(approved=True)

    def _set_as_current(self):
        """
        Sets the approver as the current active approver.
        """
        self.is_current = True
        self.status = 'Pending'
        self.save()

        # Update MinuteApproval record
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        MinuteApproval.objects.filter(minute=self.approval_chain.minute, approver=self.user).update(
            current_approver=True
        )

    # Debugging Utility
    @classmethod
    def get_approvers_status(cls, approval_chain):
        """
        Retrieve the current status of all approvers in a given approval chain.
        """
        return cls.objects.filter(approval_chain=approval_chain).values(
            'user__username',
            'order',
            'status',
            'is_current',
            'action_time'
        )
