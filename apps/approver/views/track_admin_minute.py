from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.minute.models import Minute, MinuteActionLog, MinuteApproval
from apps.approval_chain.models import Approver, ApprovalChain
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils.timezone import now
from django.http import HttpResponseNotFound


@login_required
def track_admin_minute(request, pk):
    """
    View to track the details of a specific minute, including its approval chain,
    comments/remarks, and full action history.
    Handles both in-progress and archived minutes.
    """
    # Fetch the minute and check its status
    minute = get_object_or_404(Minute, pk=pk)

    approval_chain = minute.approval_chain
    if not approval_chain:
        return HttpResponseNotFound("The approval chain for this minute does not exist.")

    approvals = MinuteApproval.objects.filter(minute=minute).select_related('approver').order_by('order')
    if not approvals.exists():
        logger.warning(f"No MinuteApproval entries found for minute ID {minute.pk}")

    action_logs = MinuteActionLog.objects.filter(minute=minute).order_by('timestamp')
    return_to_history = action_logs.filter(action='return-to')

    # Build approvers' status context
    approvers_status = []
    for approver in approval_chain.approvers.order_by('order'):
        approval_entry = approvals.filter(approver=approver.user).first()
        print(f"Processing Approver: {approver.user.username}")  # Debugging log
        print(f"Approval Entry: {approval_entry}")  # Debugging log
        if approval_entry:
            print(f"Remarks for Approver {approver.user.username}: {approval_entry.remarks}")  # Debugging log
        approvers_status.append({
            'user': approver.user,
            'status': approval_entry.status if approval_entry else 'Pending',
            'action_time': approval_entry.action_time if approval_entry else None,
            'remarks': approval_entry.remarks if approval_entry and approval_entry.remarks else "No remarks provided",
            'is_current': approval_entry and approval_entry.current_approver,
        })

    # Determine if the minute is archived
    is_archived = minute.status in ['Approved', 'Rejected']

    context = {
        'minute': minute,
        'approval_chain': approval_chain,
        'approvers_status': approvers_status,
        'action_logs': action_logs,
        'return_to_history': return_to_history,
        'timestamp': now(),
        'is_archived': is_archived,
    }

    # Allow PDF download
    if request.GET.get('download') == 'pdf':
        return generate_pdf('approver/track_minute_pdf.html', context)

    return render(request, 'approver/track_admin_minute.html', context)


def generate_pdf(template_path, context):
    """
    Generate a PDF from the given template and context.
    """
    template = get_template(template_path)
    html = template.render(context)
    response = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('UTF-8')), response)

    if not pdf.err:
        response = HttpResponse(response.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="minute_details.pdf"'
        return response
    else:
        return HttpResponse("Error generating PDF", status=500)
