from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib import messages
from apps.minute.models import MinuteApproval, MinuteActionLog
from apps.approval_chain.models import Approver
from django.utils.timezone import now
from django.db.models import Max
from django.db.models import F
from django.core.exceptions import ValidationError


User = get_user_model()

@transaction.atomic
def approve_minute(request, approval_id):
    """
    Approve the minute and move to the next approver in the chain.
    Archive if final approval is completed.
    """
    approval = get_object_or_404(MinuteApproval, id=approval_id, approver=request.user)

    # Check if the current user is authorized to approve
    if not approval.current_approver:
        return JsonResponse({'error': 'You are not the current approver for this minute.'}, status=403)

    try:
        # Get and validate remarks
        remarks = request.POST.get('remarks', '').strip()
        if not remarks:
            remarks = "Approved without additional remarks"

        # Approve the minute and update remarks
        approval.approve(remarks=remarks)

        # Archive the minute if no pending approvers remain in the chain
        if not approval.approval_chain.approvers.filter(status='Pending').exists():
            approval.minute.archive('Approved')

        # Log the action with remarks
        MinuteActionLog.objects.create(
            minute=approval.minute,
            action='approve',
            performed_by=request.user,
            remarks=remarks
        )

        # Return success response
        return JsonResponse({'success': 'Minute approved successfully.'})

    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({'error': f'Approval failed: {str(e)}'}, status=500)

@transaction.atomic
def reject_minute(request, approval_id):
    """
    Reject the minute and archive it immediately.
    """
    # Fetch the approval record, ensuring the current user is the approver
    approval = get_object_or_404(MinuteApproval, id=approval_id, approver=request.user)

    # Check if the user is authorized to reject
    if not approval.current_approver:
        return JsonResponse({'error': 'You are not the current approver for this minute.'}, status=403)

    try:
        # Capture remarks from the request
        remarks = request.POST.get('remarks', '').strip()
        if not remarks:
            remarks = "Rejected without additional remarks"

        # Reject the minute and save remarks
        approval.remarks = remarks
        approval.reject()

        # Archive the minute immediately upon rejection
        approval.minute.archive('Rejected')

        # Log the rejection action
        MinuteActionLog.objects.create(
            minute=approval.minute,
            action='reject',
            performed_by=request.user,
            remarks=remarks
        )

        # Return success response
        return JsonResponse({'success': 'Minute rejected successfully.'})

    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({'error': f'Rejection failed: {str(e)}'}, status=500)


@login_required
@transaction.atomic
def mark_to_minute(request, approval_id):
    """
    Marks the minute to another user, adding them to the approval chain with a specific order.
    """
    # Fetch the current approval record and validate the approver
    approval = get_object_or_404(MinuteApproval, id=approval_id, approver=request.user)

    if not approval.current_approver:
        return JsonResponse({'error': 'You are not the current approver for this minute.'}, status=403)

    # Extract target user ID, order, and remarks from the request
    target_user_id = request.POST.get('target_user_id')
    target_order = request.POST.get('order')
    remarks = request.POST.get('remarks', '').strip()

    # Validate input
    if not target_user_id or not target_order:
        return JsonResponse({'error': 'Both target user and order are required.'}, status=400)

    try:
        # Convert and validate the target order
        target_order = int(target_order)

        # Fetch the target user
        target_user = get_object_or_404(User, id=target_user_id)

        # Validate "Mark-To" action inputs
        validate_mark_to_input(approval, target_user, target_order)

        # Adjust the approval chain's order for the new approver
        adjust_orders(approval.approval_chain, target_order)

        # Perform the "Mark-To" action
        approval.mark_to(target_user, target_order)

        # Log the action with remarks
        log_action(
            minute=approval.minute,
            action='mark-to',
            performed_by=request.user,
            target_user=target_user,
            remarks=remarks
        )

        return JsonResponse({'success': f'Minute successfully marked to {target_user.username}.'})

    except ValidationError as e:
        # Return validation errors with a 400 status code
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({'error': f'Failed to mark the minute: {str(e)}'}, status=500)


def validate_mark_to_input(approval, target_user, target_order):
    """
    Validate the inputs for the Mark-To action.
    Ensures the target user is not already in the approval chain and the order is within a valid range.
    """
    # Check if the target user is already part of the approval chain
    if approval.approval_chain.approvers.filter(user=target_user).exists():
        raise ValidationError(f"User '{target_user.username}' is already in the approval chain.")

    # Calculate the maximum allowed order in the approval chain
    max_order = approval.approval_chain.approvers.aggregate(Max('order'))['order__max'] or 0

    # Ensure the target order is within a valid range
    if target_order < 1 or target_order > max_order + 1:
        raise ValidationError(f"Order {target_order} is out of range. Valid range: 1 to {max_order + 1}.")


@transaction.atomic
def adjust_orders(approval_chain, start_order):
    """
    Adjust the order of approvers in the approval chain, incrementing orders for approvers
    at or above the specified starting order.
    """
    if not approval_chain:
        raise ValidationError("Approval chain does not exist.")

    # Increment order for approvers starting from the specified order
    approval_chain.approvers.filter(order__gte=start_order).update(order=F('order') + 1)

def log_action(minute, action, performed_by, target_user=None, remarks=''):
    """
    Log actions performed on a minute, including optional target user and remarks.
    """
    if not minute or not action or not performed_by:
        raise ValueError("Minute, action, and performed_by are required for logging.")

    MinuteActionLog.objects.create(
        minute=minute,
        action=action,
        performed_by=performed_by,
        target_user=target_user,
        remarks=remarks.strip()  # Ensure remarks are cleanly stored
    )

@login_required
@transaction.atomic
def return_to_minute(request, approval_id):
    """
    Return the minute to a previous approver for re-evaluation.
    """
    approval = get_object_or_404(MinuteApproval, id=approval_id, approver=request.user)

    # Extract target user ID and remarks from the request
    target_user_id = request.POST.get('target_user_id')
    remarks = request.POST.get('remarks', '').strip()

    if not target_user_id:
        return JsonResponse({'error': 'Target user is required for Return-To action.'}, status=400)

    target_user = get_object_or_404(User, id=target_user_id)

    try:
        # Validate the Return-To action
        validate_return_to_input(approval, target_user)

        # Perform the Return-To action
        approval.return_to(target_user)

        # Log the Return-To action
        log_action(
            minute=approval.minute,
            action='return-to',
            performed_by=request.user,
            target_user=target_user,
            remarks=remarks
        )

        return JsonResponse({'success': f'Minute successfully returned to {target_user.username}.'})

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Return-To action failed: {str(e)}'}, status=500)

def validate_return_to_input(approval, target_user):
    """
    Validates the input for the Return-To action.
    """
    # Check if the target user has any valid approval record for this minute
    returned_approval = MinuteApproval.objects.filter(
        minute=approval.minute,
        approver=target_user
    ).first()

    if not returned_approval:
        raise ValidationError(f"User '{target_user.username}' does not have a valid approval record for this minute.")

    # Check if the minute was rejected by the target user
    if returned_approval.status == 'Rejected':
        raise ValidationError(f"Cannot return to '{target_user.username}' as they have already rejected the minute.")

    # Allow return to users who have previously approved the minute but log the action
    if returned_approval.status == 'Approved':
        print(f"Warning: Returning to '{target_user.username}' who previously approved the minute.")

    # Ensure the target approver is before or at the current approver in the chain
    if returned_approval.order >= approval.order:
        raise ValidationError(f"Cannot return to an approver with the same or higher order (order: {returned_approval.order}).")

@login_required
@transaction.atomic
def process_action(request, pk):
    """
    Handle approver actions (Approve, Reject, Mark-To, Return-To) for a minute.
    """
    minute_approval = get_object_or_404(MinuteApproval, pk=pk, approver=request.user)
    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '').strip()
    target_user_id = request.POST.get('target_user_id')

    try:
        # Validate current approver
        if not minute_approval.current_approver:
            raise ValidationError("You are not authorized to perform this action.")

        # Common log and remarks update
        def log_and_update(action_type, target_user=None):
            minute_approval.remarks = remarks
            log_action(minute_approval.minute, action_type, request.user, remarks=remarks, target_user=target_user)

        # Handle actions
        if action == 'approve':
            minute_approval.approve()

            # Archive if final approval
            if not minute_approval.approval_chain.approvers.filter(status='Pending').exists():
                minute_approval.minute.archive('Approved')

            log_and_update('approve')
            messages.success(request, "Minute approved successfully.")

        elif action == 'reject':
            minute_approval.reject()
            minute_approval.minute.archive('Rejected')
            log_and_update('reject')
            messages.success(request, "Minute rejected successfully.")

        elif action == 'mark-to':
            if not target_user_id:
                raise ValidationError("Target user is required for Mark-To action.")
            target_user = get_object_or_404(User, pk=target_user_id)
            target_order = request.POST.get('order')

            if not target_order:
                raise ValidationError("Order is required for Mark-To action.")

            # Validate and perform Mark-To
            target_order = int(target_order)
            validate_mark_to_input(minute_approval, target_user, target_order)
            adjust_orders(minute_approval.approval_chain, target_order)
            minute_approval.mark_to(target_user)

            log_and_update('mark-to', target_user)
            messages.success(request, f"Minute marked to {target_user.username}.")

        elif action == 'return-to':
            if not target_user_id:
                raise ValidationError("Target user is required for Return-To action.")
            target_user = get_object_or_404(User, pk=target_user_id)

            # Validate and perform Return-To
            validate_return_to_input(minute_approval, target_user)
            minute_approval.return_to(target_user)

            log_and_update('return-to', target_user)
            messages.success(request, f"Minute returned to {target_user.username}.")

        else:
            raise ValidationError("Invalid action.")

        # Redirect to track admin minute page on success
        return redirect('approver:track_admin_minute', pk=minute_approval.minute.pk)

    except ValidationError as e:
        messages.error(request, f"Validation Error: {e}")
        return redirect('approver:minute_details', pk=minute_approval.minute.pk)
    except Exception as e:
        messages.error(request, f"Action failed: {e}")
        return redirect('approver:minute_details', pk=minute_approval.minute.pk)
