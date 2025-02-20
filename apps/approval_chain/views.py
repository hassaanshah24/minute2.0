from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from django.views.decorators.http import require_POST
import requests
from .models import ApprovalChain, Approver
from apps.minute.models import Minute

User = get_user_model()  # Dynamically fetch the custom user model to support AUTH_USER_MODEL


@login_required
def create_approval_chain(request):
    """
    View to create or update an approval chain with dynamic approvers.
    Associates the chain with a specific minute if provided.
    """
    if request.method == "POST":
        chain_name = request.POST.get("chain_name")
        approvers = request.POST.getlist("approvers[]")
        order = request.POST.getlist("order[]")
        minute_id = request.GET.get("minute_id")

        # Validate input
        if not chain_name:
            return JsonResponse({"error": "Approval Chain Name is required!"}, status=400)
        if not approvers or not order or len(approvers) != len(order):
            return JsonResponse({"error": "Approvers and their order are required!"}, status=400)

        try:
            with transaction.atomic():
                # Create the approval chain
                chain = ApprovalChain.objects.create(name=chain_name, created_by=request.user)

                # Add approvers to the chain
                for idx, user_id in enumerate(approvers):
                    user = get_object_or_404(User, pk=user_id)
                    Approver.objects.create(
                        approval_chain=chain,
                        user=user,
                        order=int(order[idx])
                    )

                # Link the chain to the minute if minute_id is provided
                if minute_id:
                    link_chain_to_minute(chain, minute_id)

            # Redirect to the Create Minute page with the new chain pre-selected
            return redirect(build_redirect_url(chain.id, minute_id))

        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    # Handle GET request to render the form
    users = User.objects.all().order_by("username")
    minute_id = request.GET.get("minute_id")
    return render(request, "approval_chain/create_approval_chain.html", {
        "users": list(users.values("id", "username")),
        "minute_id": minute_id,
    })


@transaction.atomic
def link_chain_to_minute(chain, minute_id):
    """
    Link the given ApprovalChain to a Minute.
    Optionally updates session state via external API.
    """
    try:
        minute = get_object_or_404(Minute, pk=minute_id)
        minute.approval_chain = chain
        minute.save()

        # Optional: Update session state via external API
        update_session_state(chain.id)

    except Exception as e:
        raise RuntimeError(f"Failed to link chain to minute: {e}")


def update_session_state(chain_id):
    """
    Optional: Update the session state via external API to reflect the active chain.
    """
    api_base = settings.BASE_URL
    try:
        requests.post(
            f"{api_base}/api/chains/active/set/",
            json={"chain_id": chain_id},
            cookies=request.COOKIES
        )
    except requests.RequestException as api_error:
        print(f"API update failed: {api_error}")


def build_redirect_url(chain_id, minute_id=None):
    """
    Build the URL for redirection after chain creation.
    """
    redirect_url = f"{reverse('minute:create')}?chain_id={chain_id}"
    if minute_id:
        redirect_url += f"&minute_id={minute_id}"
    return redirect_url


@login_required
@require_POST
def delete_approval_chain(request, chain_id):
    """
    Delete an approval chain and its associated approvers.
    """
    try:
        chain = get_object_or_404(ApprovalChain, pk=chain_id)
        chain.delete()
        return JsonResponse({"success": True, "message": "Approval chain deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def reorder_approvers(request, chain_id):
    """
    Reorder approvers in the approval chain.
    """
    new_order = request.POST.getlist("order[]")
    try:
        chain = get_object_or_404(ApprovalChain, pk=chain_id)
        with transaction.atomic():
            for idx, approver_id in enumerate(new_order, start=1):
                approver = get_object_or_404(Approver, pk=approver_id, approval_chain=chain)
                approver.order = idx
                approver.save()
        return JsonResponse({"success": True, "message": "Approvers reordered successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
