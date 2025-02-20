# approver/views/minute_details.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from apps.minute.models import MinuteApproval, Minute, MinuteActionLog
from apps.approval_chain.models import Approver
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse


User = get_user_model()

@login_required
def minute_details(request, pk):
    """
    Display the details of a minute and allow approvers to take actions.
    """
    # Fetch the minute and validate its existence
    minute = get_object_or_404(Minute, pk=pk)

    # Check if the current user is an authorized approver and currently active
    current_approval = (
        MinuteApproval.objects
        .filter(minute=minute, approver=request.user, current_approver=True)
        .select_related('minute', 'approval_chain')
        .first()
    )

    if not current_approval:
        raise PermissionDenied("You are not authorized to act on this minute.")

    # Handle POST requests for actions
    if request.method == 'POST':
        return handle_post_request(request, minute, current_approval)

    # Prefetch all `MinuteApproval` objects to optimize `approvers_status`
    approvals = {
        approval.approver_id: approval
        for approval in MinuteApproval.objects.filter(minute=minute).select_related('approver')
    }

    # Fetch all approvers and their respective statuses
    approvers_status = [
        {
            'approver': approver,
            'approval': approvals.get(approver.user.id),
            'remarks': approvals.get(approver.user.id).remarks if approvals.get(approver.user.id) else "No remarks provided",
            'action_time': approvals.get(approver.user.id).action_time if approvals.get(approver.user.id) else None,
            'status': approvals.get(approver.user.id).status if approvals.get(approver.user.id) else "Pending",
            'is_current': approvals.get(approver.user.id).current_approver if approvals.get(approver.user.id) else False,
        }
        for approver in Approver.objects.filter(approval_chain=minute.approval_chain).order_by('order')
    ]

    # Fetch action logs for audit trail
    action_logs = MinuteActionLog.objects.filter(minute=minute).order_by('timestamp')

    # Prepare context for the template
    context = {
        'minute': minute,
        'current_approval': current_approval,
        'approvers_status': approvers_status,
        'action_logs': action_logs,
        'all_users': User.objects.exclude(pk=request.user.pk),
    }

    return render(request, 'approver/minute_details.html', context)


@transaction.atomic
def handle_post_request(request, minute, current_approval):
    """
    Handles POST requests for actions on a minute (approve, reject, mark-to, return-to).
    """
    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '').strip()
    target_user_id = request.POST.get('target_user')

    # Debugging logs
    logger.debug(f"Received action: {action}, Remarks: {remarks}, Target User ID: {target_user_id}")

    try:
        # Validate action and remarks
        if not action:
            raise ValidationError("No action specified.")
        if not remarks and action in [ 'mark_to', 'return_to']:
            raise ValidationError("Remarks are required for the selected action.")

        # Resolve target user if needed
        target_user = None
        if action in ['mark_to', 'return_to']:
            target_user = validate_target_user(target_user_id)

        # Perform the appropriate action
        if action == 'approve':
            current_approval.approve(remarks=remarks)
        elif action == 'reject':
            current_approval.reject(remarks=remarks)
        elif action == 'mark_to':
            current_approval.mark_to(target_user=target_user, remarks=remarks)
        elif action == 'return_to':
            current_approval.return_to(target_user=target_user, remarks=remarks)
        else:
            raise ValidationError(f"Invalid action: {action}")

        # Log the action
        log_minute_action(minute, action, request.user, target_user, remarks)
        logger.debug(f"Remarks received in POST request: {remarks}")

        # Provide success feedback
        messages.success(request, f"Action '{action.replace('_', ' ').title()}' performed successfully.")
        return redirect('approver:track_minute', pk=minute.pk)

    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        messages.error(request, f"Validation Error: {str(ve)}")
    except Exception as e:
        logger.exception("Unhandled error during POST request")
        messages.error(request, f"Action failed: {str(e)}")

    # Redirect back to the minute details page
    return redirect('approver:minute_details', pk=minute.pk)

def validate_target_user(target_user_id):
    """
    Validate and return the target user for mark-to or return-to actions.

    Args:
        target_user_id (int): The ID of the target user.

    Returns:
        User: The validated target user.

    Raises:
        ValidationError: If the target user is invalid or does not exist.
    """
    if not target_user_id:
        raise ValidationError("Target user ID must be provided.")

    try:
        target_user = User.objects.get(pk=target_user_id)
    except User.DoesNotExist:
        raise ValidationError("The specified target user does not exist.")

    # Additional validation if necessary (e.g., user role checks)
    if not target_user.is_active:
        raise ValidationError(f"The target user '{target_user.username}' is inactive.")

    return target_user


def log_minute_action(minute, action, performed_by, target_user=None, remarks=""):
    """
    Log an action taken on a minute for tracking purposes.

    Args:
        minute (Minute): The minute on which the action is performed.
        action (str): The action taken (approve, reject, mark-to, return-to).
        performed_by (User): The user performing the action.
        target_user (User, optional): The target user for mark-to or return-to actions.
        remarks (str, optional): Additional remarks for the action.

    Returns:
        MinuteActionLog: The newly created log entry.
    """
    if not action:
        raise ValidationError("Action type must be specified for logging.")

    if action in ['mark-to', 'return-to'] and not target_user:
        raise ValidationError(f"Target user is required for '{action}' action.")

    log_entry = MinuteActionLog.objects.create(
        minute=minute,
        action=action,
        performed_by=performed_by,
        target_user=target_user,
        remarks=remarks or f"{action.capitalize()} action performed by {performed_by.get_full_name()}",
    )

    # For debugging/logging the creation process
    print(f"Action Log Created: {log_entry}")

    return log_entry
