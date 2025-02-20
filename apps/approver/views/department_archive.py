from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.minute.models import Minute, MinuteApproval
from apps.approval_chain.models import Approver

@login_required
def department_archive(request):
    """
    Display all archived minutes where the current user:
    1️⃣ Was an approver in the chain.
    2️⃣ Belongs to the department of the minute.
    """

    user = request.user
    user_department = user.department if hasattr(user, 'department') else None

    # ✅ Fetch archived minutes where the user was an approver
    approver_minutes = Minute.objects.filter(
        approval_chain__approvers__user=user,
        status__in=['Approved', 'Rejected'],
        archived=True
    ).distinct()

    # ✅ Fetch archived minutes where the minute belongs to the user's department
    department_minutes = Minute.objects.filter(
        department=user_department,
        status__in=['Approved', 'Rejected'],
        archived=True
    ).distinct() if user_department else Minute.objects.none()

    # ✅ Combine results (Avoid duplicates using `distinct()`)
    archived_minutes = (approver_minutes | department_minutes).distinct()

    # ✅ Build context for archived minutes
    minutes_with_approvers = []
    for minute in archived_minutes:
        approvals = MinuteApproval.objects.filter(minute=minute).select_related('approver').order_by('order')
        approvers_status = []
        for approver in minute.approval_chain.approvers.order_by('order'):
            approval_entry = approvals.filter(approver=approver.user).first()
            approvers_status.append({
                'user': approver.user,
                'user_full_name': approver.user.get_full_name() if approver.user else "Unknown User",
                'status': approval_entry.status if approval_entry else 'Pending',
                'action_time': approval_entry.action_time.strftime("%d-%b-%Y %H:%M") if approval_entry and approval_entry.action_time else "Pending",
                'remarks': approval_entry.remarks if approval_entry else "No remarks provided",
            })

        minutes_with_approvers.append({
            'minute': minute,
            'approvers_status': approvers_status,
        })

    context = {
        'archived_minutes': minutes_with_approvers,
    }

    return render(request, 'approver/department_archive.html', context)
