from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.minute.models import MinuteApproval
from apps.approval_chain.models import Approver

@receiver(post_save, sender=Approver)
def sync_approver_with_minute_approval(sender, instance, **kwargs):
    """
    Synchronize Approver's status and current approver flag with MinuteApproval.
    Ensures that changes to Approver's status or is_current field are reflected in the related MinuteApproval.
    """
    MinuteApproval.objects.filter(
        approval_chain=instance.approval_chain,
        approver=instance.user
    ).update(
        status=instance.status,
        current_approver=instance.is_current,
        action_time=instance.action_time
    )

@receiver(post_delete, sender=Approver)
def handle_approver_deletion(sender, instance, **kwargs):
    """
    Handle the deletion of an Approver by removing the corresponding MinuteApproval.
    Ensures that the approval chain and minute approvals remain consistent.
    """
    MinuteApproval.objects.filter(
        approval_chain=instance.approval_chain,
        approver=instance.user
    ).delete()
