from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from apps.minute.models import MinuteApproval

@login_required
def dashboard(request):
    """
    Render the Approver Dashboard.

    Displays:
    - List of pending minutes assigned to the logged-in approver.
    - Summary statistics of approval tasks.
    """
    user = request.user

    # Aggregate statistics for dashboard summary
    stats = MinuteApproval.objects.filter(approver=user).aggregate(
        total_pending=Count('id', filter=Q(status='Pending', current_approver=True)),
        total_approved=Count('id', filter=Q(status='Approved')),
        total_rejected=Count('id', filter=Q(status='Rejected'))
    )

    # Retrieve pending approvals efficiently
    pending_approvals = (
        MinuteApproval.objects.filter(
            approver=user,
            current_approver=True,
            status='Pending'
        )
        .select_related('minute')  # Use select_related only for 'minute' to avoid conflicts
        .prefetch_related('minute__created_by')  # Prefetch related user data for efficiency
        .order_by('-minute__created_at')
    )

    # Context for template
    context = {
        'pending_approvals': pending_approvals,
        'total_pending': stats['total_pending'],
        'total_approved': stats['total_approved'],
        'total_rejected': stats['total_rejected'],
    }

    return render(request, 'approver/dashboard.html', context)
