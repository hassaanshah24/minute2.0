from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Max
from apps.minute.models import Minute, MinuteApproval
from apps.approval_chain.models import ApprovalChain, Approver
from .serializers import (
    MinuteSerializer,
    ApprovalChainSerializer,
    UserSerializer,
    ApproverSerializer,
)



User = get_user_model()


class MinuteAPIView(APIView):
    """
    API for managing Minute creation, draft, and submission.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        """
        Handles creating or updating a minute.
        Distinguishes between saving as a draft and submitting.
        """

        minute_id = request.data.get("minute_id")
        is_submit = request.data.get("submit", False)  # True for submission
        data = request.data

        if minute_id:
            minute = get_object_or_404(Minute, pk=minute_id)
            serializer = MinuteSerializer(minute, data=data, partial=True)
        else:
            serializer = MinuteSerializer(data=data)

        if serializer.is_valid():
            with transaction.atomic():
                # Save minute (draft or new submission)
                minute = serializer.save(created_by=request.user)

                if is_submit:
                    # Handle submission-specific logic
                    approval_chain_id = data.get("approval_chain")
                    if not approval_chain_id:
                        return Response(
                            {"error": "Approval chain is required for submission."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    approval_chain = get_object_or_404(ApprovalChain, pk=approval_chain_id)
                    minute.approval_chain = approval_chain
                    minute.status = "Submitted"
                    minute.save()

                    # Initialize approval process
                    self._initialize_approval_process(minute, approval_chain)

                return Response(
                    {"message": "Minute saved successfully.", "minute": serializer.data},
                    status=status.HTTP_201_CREATED,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _initialize_approval_process(self, minute, approval_chain):
        """
        Initializes the approval process by creating the first approver record.
        """
        first_approver = approval_chain.approvers.order_by("order").first()
        if not first_approver:
            raise ValidationError("Approval Chain has no approvers.")

        MinuteApproval.objects.create(
            minute=minute,
            approval_chain=approval_chain,
            approver=first_approver.user,
            status="Pending",
            current_approver=True,
            order=first_approver.order,  # Explicitly set the order
        )
        logger.info(f"Approval process initialized for minute: {minute.id}")

    def get(self, request, *args, **kwargs):
        """
        Retrieves minute details by ID.
        """
        minute_id = kwargs.get("minute_id")
        if not minute_id:
            return Response({"error": "minute_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        minute = get_object_or_404(Minute, pk=minute_id)
        serializer = MinuteSerializer(minute)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApprovalChainAPIView(APIView):
    """
    API for managing Approval Chains.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Creates an Approval Chain and assigns approvers.
        """
        data = request.data
        serializer = ApprovalChainSerializer(data=data)

        if serializer.is_valid():
            with transaction.atomic():
                chain = serializer.save(created_by=request.user)
                approvers = data.get("approvers", [])
                orders = data.get("order", [])

                if len(approvers) != len(orders):
                    return Response({"error": "Approvers and orders must match."}, status=status.HTTP_400_BAD_REQUEST)

                # Add approvers to the chain
                for idx, user_id in enumerate(approvers):
                    user = get_object_or_404(User, pk=user_id)
                    Approver.objects.create(
                        approval_chain=chain,
                        user=user,
                        order=orders[idx],
                    )

                return Response(
                    {"message": "Approval chain created successfully.", "chain_id": chain.id},
                    status=status.HTTP_201_CREATED,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        """
        Retrieves Approval Chain details by ID.
        """
        chain_id = kwargs.get("chain_id")
        if not chain_id:
            return Response({"error": "chain_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        chain = get_object_or_404(ApprovalChain, pk=chain_id)
        serializer = ApprovalChainSerializer(chain)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubmitMinuteAPIView(APIView):
    """
    Submits a Minute and assigns the approval chain.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Links a minute with an approval chain and initializes the approval process.
        """
        data = request.data
        minute_id = data.get("minute_id")
        approval_chain_id = data.get("approval_chain")

        if not minute_id or not approval_chain_id:
            return Response({"error": "minute_id and approval_chain are required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            minute = get_object_or_404(Minute, pk=minute_id)
            approval_chain = get_object_or_404(ApprovalChain, pk=approval_chain_id)

            # Link chain and update status
            minute.approval_chain = approval_chain
            minute.status = "Submitted"
            minute.save()

            # Initialize approval process
            self._initialize_approval_process(minute, approval_chain)

        return Response({"message": "Minute submitted successfully.", "minute_id": minute.id},
                        status=status.HTTP_200_OK)


class UpdateMinuteStatusAPIView(APIView):
    """
    API to handle the four actions: approve, reject, mark-to, return-to.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handles actions performed by approvers on a minute.
        """
        minute_id = kwargs.get('minute_id')
        action = request.data.get('action')  # approve, reject, mark-to, return-to
        target_user_id = request.data.get('target_user')  # For mark-to or return-to actions
        current_user = request.user

        # Validate the provided action
        if not minute_id or action not in ['approve', 'reject', 'mark-to', 'return-to']:
            return Response({"error": "Invalid action or missing data."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the Minute and its corresponding MinuteApproval
        minute = get_object_or_404(Minute, pk=minute_id)
        approval = get_object_or_404(MinuteApproval, minute=minute, approver=current_user, status='Pending')

        with transaction.atomic():
            if action == 'approve':
                self._approve_action(minute, approval)

            elif action == 'reject':
                self._reject_action(minute, approval)

            elif action == 'mark-to':
                if not target_user_id:
                    return Response({"error": "Target user is required for mark-to action."}, status=status.HTTP_400_BAD_REQUEST)
                self._mark_to_action(minute, approval, target_user_id)

            elif action == 'return-to':
                if not target_user_id:
                    return Response({"error": "Target user is required for return-to action."}, status=status.HTTP_400_BAD_REQUEST)
                self._return_to_action(minute, approval, target_user_id)

            # Save changes
            approval.save()
            minute.save()

        return Response({"message": f"Action '{action}' performed successfully.", "status": approval.status}, status=status.HTTP_200_OK)

    def _approve_action(self, minute, approval):
        """
        Handles the 'approve' action.
        """
        approval.status = 'Approved'
        approval.action = 'approve'
        approval.action_time = now()
        approval.current_approver = False

        # Fetch the current approver's order
        current_approver = get_object_or_404(Approver, approval_chain=approval.approval_chain, user=approval.approver)
        current_order = current_approver.order

        # Move to the next approver in the chain
        next_approver = (
            approval.approval_chain.approvers
            .filter(order__gt=current_order)
            .order_by('order')
            .first()
        )

        if next_approver:
            # Create a new approval record for the next approver
            MinuteApproval.objects.create(
                minute=minute,
                approval_chain=approval.approval_chain,
                approver=next_approver.user,
                status='Pending',
                current_approver=True
            )
        else:
            # If no next approver, mark the minute as fully approved
            minute.status = 'Approved'

    def _reject_action(self, minute, approval):
        """
        Handles the 'reject' action.
        """
        approval.status = 'Rejected'
        approval.action = 'reject'
        approval.action_time = now()
        approval.current_approver = False
        minute.status = 'Rejected'

    def _mark_to_action(self, minute, approval, target_user_id):
        """
        Handles the 'mark-to' action.
        """
        target_user = get_object_or_404(User, pk=target_user_id)

        # Add a new approver to the chain with the highest order
        last_order = approval.approval_chain.approvers.aggregate(Max('order'))['order__max'] or 0
        new_approver = Approver.objects.create(
            approval_chain=approval.approval_chain,
            user=target_user,
            order=last_order + 1
        )

        # Create a new pending approval record for the marked approver
        MinuteApproval.objects.create(
            minute=minute,
            approval_chain=approval.approval_chain,
            approver=new_approver.user,
            status='Pending',
            current_approver=True
        )

    def _return_to_action(self, minute, approval, target_user_id):
        """
        Handles the 'return-to' action.
        """
        target_user = get_object_or_404(User, pk=target_user_id)

        # Ensure the target user is part of the approval chain
        approver = approval.approval_chain.approvers.filter(user=target_user).first()
        if not approver:
            raise ValidationError({"error": "Target user is not in the approval chain."})

        # Create a new pending approval record for the returned approver
        MinuteApproval.objects.create(
            minute=minute,
            approval_chain=approval.approval_chain,
            approver=target_user,
            status='Pending',
            current_approver=True
        )

        approval.status = 'Returned'
        approval.action = 'return-to'
        approval.action_time = now()
        approval.current_approver = False