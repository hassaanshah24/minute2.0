# approver/views/approval_tracker.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.minute.models import Minute, MinuteActionLog
from apps.approval_chain.models import Approver

@login_required
def approval_tracker(request):
    """
    Displays all minutes where the user has participated in the approval process or is in the chain.
    """
    user = request.user

    # Fetch all minutes where the user is in the approval chain
    in_approval_chain = Minute.objects.filter(approval_chain__approvers__user=user).distinct()

    # Fetch all minutes where the user has performed actions
    action_logs = MinuteActionLog.objects.filter(performed_by=user).values_list('minute', flat=True)
    with_actions = Minute.objects.filter(pk__in=action_logs).distinct()

    # Combine both querysets
    related_minutes = (in_approval_chain | with_actions).distinct()

    context = {
        'related_minutes': related_minutes,
    }

    return render(request, 'approver/approval_tracker.html', context)
