from django.urls import reverse
from django.views.generic import CreateView, TemplateView, ListView, DetailView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from apps.minute.models import Minute, MinuteApproval
from apps.minute.forms import MinuteForm
from apps.approval_chain.models import ApprovalChain
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.generic.edit import CreateView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.core.serializers.json import DjangoJSONEncoder
import textwrap
from django.template.loader import get_template
import pdfkit


class CreateMinuteView(LoginRequiredMixin, CreateView):
    """
    View for creating or editing a minute document.
    Handles new and existing minutes based on minute_id and chain_id parameters.
    """
    model = Minute
    form_class = MinuteForm
    template_name = 'minute/create_minute.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Handle the minute and approval chain setup for new or existing instances.
        """
        self.minute_id = self.request.GET.get('minute_id')
        self.chain_id = self.request.GET.get('chain_id')
        self.minute_instance = None
        self.selected_chain = None

        # Fetch existing minute if `minute_id` is provided
        if self.minute_id:
            self.minute_instance = get_object_or_404(Minute, pk=self.minute_id)

        # Fetch and link the approval chain if `chain_id` is provided
        if self.chain_id:
            self.selected_chain = self._get_approval_chain()

        return super().dispatch(request, *args, **kwargs)

    def _get_approval_chain(self):
        """
        Fetch and link the approval chain to the minute if applicable.
        """
        try:
            chain = ApprovalChain.objects.get(pk=self.chain_id)
            if self.minute_instance and not self.minute_instance.approval_chain:
                self.minute_instance.approval_chain = chain
                self.minute_instance.save()
            return chain
        except ApprovalChain.DoesNotExist:
            return None

    def get_initial(self):
        """
        Prepopulate form fields when editing an existing minute.
        """
        initial = super().get_initial()
        if self.minute_instance:
            initial.update({
                'title': self.minute_instance.title,
                'subject': self.minute_instance.subject,
                'description': self.minute_instance.description,
                'sheet_number': self.minute_instance.sheet_number,
            })
        return initial


    def get_context_data(self, **kwargs):
        """
        Add approval chain details and list of available chains to the context.
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'approval_chains': ApprovalChain.objects.all(),
            'minute': self.minute_instance,
            'selected_chain': self.selected_chain,
        })
        return context

    def form_valid(self, form):
        """
        Validates, saves, and processes the approval workflow.
        """
        form.instance.created_by = self.request.user  # Set the user who created the minute

        # ✅ Explicitly Assign Department to Minute (to avoid validation errors)
        if hasattr(self.request.user, 'department'):
            form.instance.department = self.request.user.department
        else:
            raise ValidationError("User does not have an assigned department.")

        self.object = form.save(commit=False)

        # Ensure document ID and approval chain are assigned correctly
        self._assign_unique_id()
        self._assign_approval_chain()

        # Prevent submission without an approval chain
        if self.object.status == 'Submitted' and not self.object.approval_chain:
            raise ValidationError("A Minute must be linked to an approval chain before submission.")

        self.object.save()

        # Ensure approval process starts if the minute is submitted
        if self.object.status == 'Submitted' and self.object.approval_chain:
            self._initialize_approval_process()

        return self._redirect_after_save()

    def get_form_kwargs(self):
        """
        Pass additional arguments to the form (like request).
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Pass request to form to auto-set department
        return kwargs

    def _assign_unique_id(self):
        """
        Assigns a unique university-standard minute ID before saving.
        Format: DHA/DSU/<Department>/<MM-YYYY>/<####>
        """
        if not self.object.unique_id:
            self.object.unique_id = self.object._generate_unique_id()

    def _assign_approval_chain(self):
        """
        Assign the selected approval chain to the minute.
        """
        approval_chain_id = self.request.POST.get('approval_chain') or self.chain_id
        if approval_chain_id:
            try:
                chain = ApprovalChain.objects.get(pk=approval_chain_id)
                if not self.object.approval_chain:  # Link only if not already linked
                    self.object.approval_chain = chain
                self.object.status = 'Submitted'  # Mark as submitted if chain is assigned
            except ApprovalChain.DoesNotExist:
                self.object.status = 'Draft'
        else:
            self.object.status = 'Draft'

    def _initialize_approval_process(self):
        """
        Initialize approval records for all approvers.
        """
        approvers = self.object.approval_chain.approvers.order_by('order')

        if not approvers.exists():
            raise ValidationError("ApprovalChain must have at least one approver.")

        # **FIX: Ensure all approvers are assigned, not just the first one**
        with transaction.atomic():
            for approver in approvers:
                MinuteApproval.objects.create(
                    minute=self.object,
                    approval_chain=self.object.approval_chain,
                    approver=approver.user,
                    order=approver.order,
                    status='Pending',
                    current_approver=(approver.order == 1)  # First approver is current
                )

    def _redirect_after_save(self):
        """
        Redirect to the correct page based on minute's status.
        """
        if self.object.status == 'Submitted':
            # Redirect to tracking page after submission
            return redirect(reverse('minute:track_detail', kwargs={'pk': self.object.pk}))
        else:
            # **Fix: Redirect back to the existing minute instead of a new form**
            return redirect(reverse('minute:create') + f"?minute_id={self.object.pk}")

class SubmitMinuteSuccessView(LoginRequiredMixin, TemplateView):
    """
    Display success message and details of a submitted minute.
    """
    template_name = 'minute/submit_minute_success.html'

    def get_context_data(self, **kwargs):
        """
        Add minute details and approval chain to the context.
        """
        context = super().get_context_data(**kwargs)

        # Fetch the Minute object
        minute = get_object_or_404(Minute, pk=kwargs['minute_id'])

        # Retrieve the approval chain and approvers
        try:
            chain = minute.approval_chain  # Using the related name defined in models
            approvers = chain.approvers.order_by('order') if chain else []
        except ApprovalChain.DoesNotExist:
            chain = None
            approvers = []

        # Add data to context
        context.update({
            'minute': minute,
            'approval_chain': chain,
            'approvers': approvers,
            'can_download': chain is not None,  # Allow download only if a chain exists
        })

        return context


class TrackMinuteView(LoginRequiredMixin, ListView):
    model = Minute
    template_name = 'minute/track_minute.html'
    context_object_name = 'minutes'

    def get_queryset(self):
        """
        Retrieve all minutes with statuses indicating they are in progress (not archived).
        Only show minutes with statuses 'Submitted', 'Pending', 'Marked', or 'Returned'.
        """
        return Minute.objects.filter(
            status__in=['Submitted', 'Pending', 'Marked', 'Returned']
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        """
        Add approval chains and approvers' statuses to the context.
        """
        context = super().get_context_data(**kwargs)

        approval_chains = {}
        approvers_status_map = {}

        for minute in context['minutes']:
            chain = minute.approval_chain
            approvers_status = []

            if chain:
                for approver in chain.approvers.order_by('order'):
                    approval_entry = minute.approvals.filter(approver=approver.user).first()
                    approvers_status.append({
                        'approver': approver.user.username,
                        'status': approval_entry.status if approval_entry else 'Pending',
                        'action_time': approval_entry.action_time if approval_entry else None,
                        'remarks': approval_entry.remarks if approval_entry else None,
                        'is_current': approval_entry and approval_entry.current_approver,
                    })

            approval_chains[minute.id] = list(chain.approvers.all()) if chain else []
            approvers_status_map[minute.id] = approvers_status

        context['approval_chains'] = approval_chains
        context['approvers_status_map'] = approvers_status_map

        # Debugging logs to verify data
        print("Approval Chains:", context['approval_chains'])
        print("Approvers Status Map:", context['approvers_status_map'])

        return context

class ArchiveView(LoginRequiredMixin, ListView):
    """
    View to display archived minutes (Approved/Rejected).
    """
    model = Minute
    template_name = 'minute/archive.html'
    context_object_name = 'archived_minutes'  # ✅ Fix: Ensure correct variable name

    def get_queryset(self):
        """
        Retrieve archived minutes (Approved/Rejected) only.
        """
        return Minute.objects.filter(
            created_by=self.request.user,
            status__in=['Approved', 'Rejected'],  # Ensure only final statuses are included
            archived=True  # ✅ Fix: Ensure only minutes marked as archived appear
        ).order_by('-updated_at')  # Sort by last update time


import re


class TrackMinuteDetailView(LoginRequiredMixin, DetailView):
    """
    Display details and approval progress of a specific minute.
    Includes a success message for submitted minutes.
    """
    model = Minute
    template_name = 'minute/track_minute_detail.html'
    context_object_name = 'minute'

    def split_description_into_pages(self, description, words_per_page=150):
        """
        Splits the description into pages while keeping sentences intact.
        """
        if not description or not isinstance(description, str):
            return ["No description available."]

        # Sentence-based splitting to avoid cutting sentences awkwardly
        sentences = re.split(r'(?<=[.!?])\s+', description.strip())

        pages = []
        current_page = ""

        for sentence in sentences:
            if len(current_page.split()) + len(sentence.split()) <= words_per_page:
                current_page += sentence + " "
            else:
                pages.append(current_page.strip())
                current_page = sentence + " "

        if current_page:
            pages.append(current_page.strip())  # Append last page

        return pages

    def get_context_data(self, **kwargs):
        """
        Add approvers' status, paginated description, and success message to the context.
        """
        context = super().get_context_data(**kwargs)
        minute = self.get_object()
        chain = getattr(minute, 'approval_chain', None)

        # ✅ Read current page from request GET
        try:
            current_page = int(self.request.GET.get("page", 1))  # Default to 1
        except ValueError:
            current_page = 1  # Fallback if invalid

        # ✅ Paginate description
        description_pages = self.split_description_into_pages(minute.description, words_per_page=150)
        total_pages = len(description_pages)

        # ✅ Ensure current page is within range
        current_page = max(1, min(current_page, total_pages))

        # ✅ Get content for current page
        current_description = description_pages[current_page - 1] if description_pages else "No content available."

        # ✅ Fetch approval chain details
        approvers_status = []
        current_approver = None
        return_to_history = []

        if chain:
            for approver in chain.approvers.order_by('order'):
                approval_entry = minute.approvals.filter(approver=approver.user).first()
                approvers_status.append({
                    'approver': approver.user.username,
                    'status': approval_entry.status if approval_entry else 'Pending',
                    'action_time': approval_entry.action_time if approval_entry else None,
                    'remarks': approval_entry.remarks if approval_entry else None,
                    'is_current': approval_entry and approval_entry.current_approver,
                })
                if approval_entry and approval_entry.current_approver:
                    current_approver = approver.user.username

        show_success_message = minute.status == 'Submitted'

        # ✅ Update context with paginated description and approval details
        context.update({
            'approval_chain': chain,
            'approvers_status': approvers_status,
            'current_approver': current_approver,
            'return_to_history': return_to_history,
            'show_success_message': show_success_message,
            'success_message': "Your minute has been successfully submitted and is now pending approval.",
            'description_pages': description_pages,  # 🔥 Add paginated description
            'current_description': current_description,  # 🔥 Only show current page's content
            'total_pages': total_pages,  # 🔥 Track total pages
            'current_page': current_page,  # 🔥 Start from correct page
        })

        return context


class ApprovalChainStatusView(View):
    """
    API View to fetch real-time approval chain status for a minute.
    """

    def get(self, request, minute_id, *args, **kwargs):
        """
        Returns JSON data for the approval chain status.
        """
        try:
            minute = Minute.objects.get(pk=minute_id)

            # ✅ FIX: Explicitly order approvals by 'order' field
            approvals = MinuteApproval.objects.filter(minute=minute).order_by('order')

            # If no approvals found, return a message
            if not approvals.exists():
                return JsonResponse({"error": "No approvals found for this minute."}, status=404)

            approval_chain_data = []
            for approval in approvals:
                approver_name = approval.approver.get_full_name() if approval.approver and approval.approver.get_full_name() else approval.approver.username if approval.approver else "Unknown"

                approval_chain_data.append({
                    "approver": approver_name,
                    "status": approval.status,
                    "action": approval.action if approval.action else "No action",
                    "remarks": approval.remarks if approval.remarks else "No remarks provided",
                    "action_time": approval.action_time.strftime(
                        "%d-%b-%Y %H:%M") if approval.action_time else "Pending",
                    "current_approver": approval.current_approver,
                    "order": approval.order  # ✅ FIX: Ensure 'order' is included in the response
                })

            return JsonResponse({"approval_chain": approval_chain_data}, encoder=DjangoJSONEncoder)

        except Minute.DoesNotExist:
            return JsonResponse({"error": "Minute not found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)





def preview_minute_sheet(request, minute_id):
    """
    Preview the formatted minute sheet with automatic pagination.
    """
    minute = get_object_or_404(Minute, pk=minute_id)
    approval_chain = getattr(minute, 'approval_chain', None)

    # ✅ Read current page from request GET
    try:
        page = int(request.GET.get("page", 1))  # Default to 1
    except ValueError:
        page = 1  # Fallback if invalid

    # ✅ Define words per page
    MAX_WORDS_PER_PAGE = 200

    # ✅ Paginate description
    description_pages = split_description_into_pages(minute.description, MAX_WORDS_PER_PAGE)
    total_pages = len(description_pages)

    # ✅ Ensure page is within range
    page = max(1, min(page, total_pages))

    # ✅ Get content for current page
    current_description = description_pages[page - 1] if description_pages else "No content available."

    # ✅ Fetch Approval Chain & Approvers
    approvers_status = []
    if approval_chain:
        for approver in approval_chain.approvers.order_by('order'):
            approval_entry = MinuteApproval.objects.filter(minute=minute, approver=approver.user).first()
            approvers_status.append({
                'approver': approver.user.get_full_name(),
                'status': approval_entry.status if approval_entry else 'Pending',
                'action_time': approval_entry.action_time.strftime(
                    "%d-%b-%Y %H:%M") if approval_entry and approval_entry.action_time else "Pending",
                'remarks': approval_entry.remarks if approval_entry else "No remarks provided",
                'is_current': approval_entry and approval_entry.current_approver,
            })

    return render(request, 'minute/minute_sheet.html', {
        'minute': minute,
        'approval_chain': approval_chain,
        'approvers_status': approvers_status,
        'current_description': current_description,
        'total_pages': total_pages,
        'current_page': page,
    })



def split_description_into_pages(description, words_per_page=200):
    """
    Automatically splits long descriptions into multiple pages, keeping sentences intact.
    """
    if not description or not isinstance(description, str):
        return ["No description available."]

    words = description.split()
    pages = [" ".join(words[i:i + words_per_page]) for i in range(0, len(words), words_per_page)]

    return pages


class GenerateMinutePDFView(View):
    """
    Generates a PDF of the minute sheet with proper formatting.
    """
    def get(self, request, minute_id, *args, **kwargs):
        minute = get_object_or_404(Minute, id=minute_id)

        # ✅ Fetch approval chain (Static for PDF)
        approvals = MinuteApproval.objects.filter(minute=minute).order_by('order')
        approval_chain_text = " ---> ".join([
            f"{approval.approver.get_full_name()} ({approval.status})"
            for approval in approvals
        ])

        # ✅ Paginate description properly
        MAX_WORDS_PER_PAGE = 200  # Ensure it matches the Track/Preview logic
        description_pages = split_description_into_pages(minute.description, MAX_WORDS_PER_PAGE)

        # ✅ Merge all description pages for the PDF (no Next/Prev needed)
        full_description = "\n\n".join(description_pages)  # Ensure smooth merging

        # ✅ Render template with full description (No Pagination)
        template = get_template("minute/minute_pdf_template.html")  # ✅ Use a separate template for PDFs
        html_content = template.render({
            "minute": minute,
            "full_description": full_description,  # ✅ Use the combined description
            "approval_chain_text": approval_chain_text,  # ✅ Static rendering of the approval chain
        })

        # ✅ PDF Generation Options (Ensure Proper Formatting)
        pdf_options = {
            'page-size': 'A4',
            'margin-top': '15mm',
            'margin-right': '15mm',
            'margin-bottom': '15mm',
            'margin-left': '15mm',
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'no-outline': None,
        }

        # ✅ Generate PDF
        pdf = pdfkit.from_string(html_content, False, options=pdf_options,
                                 configuration=pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))

        # ✅ Return as a downloadable file
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Minute_{minute.unique_id}.pdf"'
        return response
