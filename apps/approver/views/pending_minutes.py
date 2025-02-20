# approver/views/pending_minutes.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.minute.models import MinuteApproval
from datetime import datetime

@login_required
def pending_minutes(request):
    """
    View to display all pending minutes for the logged-in approver.
    Provides search, filter, and pagination functionality.
    """
    user = request.user
    query = request.GET.get('query', '').strip()  # Search query for minute title
    submitter = request.GET.get('submitter', '').strip()  # Filter by submitter username
    start_date = request.GET.get('start_date', '').strip()  # Filter by start date
    end_date = request.GET.get('end_date', '').strip()  # Filter by end date

    # Base query: Pending minutes where the user is the current approver
    approvals = MinuteApproval.objects.filter(
        approver=user,
        current_approver=True,
        status='Pending'
    ).select_related('minute__created_by').order_by('-minute__created_at')

    # Apply search and filters
    if query:
        approvals = approvals.filter(minute__title__icontains=query)
    if submitter:
        approvals = approvals.filter(minute__created_by__username__icontains=submitter)
    if start_date and end_date:
        try:
            # Convert string dates to datetime objects
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            approvals = approvals.filter(minute__created_at__date__range=[start_date_obj, end_date_obj])
        except ValueError:
            pass  # Ignore invalid date formats

    # Paginate results (10 per page)
    paginator = Paginator(approvals, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.get_page(1)  # Default to the first page if invalid

    context = {
        'page_obj': page_obj,
        'query': query,
        'submitter': submitter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'approver/pending_minutes.html', context)
