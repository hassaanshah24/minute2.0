from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from apps.minute.models import Minute, MinuteApproval
from apps.approval_chain.models import ApprovalChain, Approver

@receiver(post_save, sender=Minute)
def create_approval_chain_for_minute(sender, instance, created, **kwargs):
    """
    Automatically create an ApprovalChain when a new Minute is created, ensuring it is properly linked.
    """
    if created and not instance.approval_chain:
        approval_chain = ApprovalChain.objects.create(
            name=f"Approval Chain for {instance.title}",
            created_by=instance.created_by,
            minute=instance  # Link approval chain to minute
        )
        instance.approval_chain = approval_chain
        instance.save()


@receiver(post_save, sender=MinuteApproval)
def sync_minute_approval_with_chain(sender, instance, **kwargs):
    """
    Synchronize the status of the ApprovalChain with its associated MinuteApprovals.
    If all approvals are completed, mark the ApprovalChain as 'Completed'.
    If any approver rejects, the minute is marked as 'Rejected'.
    """
    approval_chain = instance.approval_chain

    # If no approvals are pending, set the chain's status to 'Completed'
    if not approval_chain.minute_approvals.filter(status='Pending').exists():
        approval_chain.status = 'Completed'
        approval_chain.save(update_fields=['status'])

    # If any approver rejected, set the chain and minute to 'Rejected'
    if approval_chain.minute_approvals.filter(status='Rejected').exists():
        approval_chain.status = 'Completed'  # Approval chain is completed if rejected
        approval_chain.minute.status = 'Rejected'
        approval_chain.save(update_fields=['status'])
        approval_chain.minute.save(update_fields=['status'])


@receiver(post_save, sender=MinuteApproval)
def set_next_current_approver(sender, instance, **kwargs):
    """
    Automatically progress to the next approver in sequence when an approver completes their action.
    If no next approver exists, the approval chain and minute are marked as 'Approved'.
    """
    if instance.status == 'Approved':
        try:
            # Get the current approver's order
            approver_entry = Approver.objects.get(
                approval_chain=instance.approval_chain,
                user=instance.approver
            )
            current_order = approver_entry.order

            # Find the next approver
            next_approver = instance.approval_chain.approvers.filter(order__gt=current_order, status='Pending').first()

            if next_approver:
                # Set the next approver's MinuteApproval as the current approver
                next_minute_approval = MinuteApproval.objects.filter(
                    approval_chain=instance.approval_chain,
                    approver=next_approver.user
                ).first()

                if next_minute_approval:
                    next_minute_approval.current_approver = True
                    next_minute_approval.save(update_fields=['current_approver'])

                    # Mark the next approver as current in the Approver model
                    next_approver.is_current = True
                    next_approver.save(update_fields=['is_current'])
            else:
                # No next approver; mark the minute and chain as approved
                instance.approval_chain.status = 'Completed'
                instance.approval_chain.minute.status = 'Approved'
                instance.approval_chain.save(update_fields=['status'])
                instance.approval_chain.minute.save(update_fields=['status'])

        except Approver.DoesNotExist:
            # Safety catch: if no approver entry exists, log an error
            pass
