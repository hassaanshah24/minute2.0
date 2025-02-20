from rest_framework import serializers
from apps.minute.models import Minute, MinuteApproval
from apps.approval_chain.models import ApprovalChain, Approver
from django.contrib.auth import get_user_model

User = get_user_model()


class MinuteSerializer(serializers.ModelSerializer):
    """
    Serializer for the Minute model.
    Handles creation, validation, and read-only fields for the approval workflow.
    """
    created_by = serializers.StringRelatedField(read_only=True)
    approval_chain = serializers.StringRelatedField(read_only=True)
    unique_id = serializers.CharField(read_only=True)
    attachment = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Minute
        fields = [
            'id',
            'title',
            'subject',
            'description',
            'attachment',
            'approval_chain',
            'status',
            'created_by',
            'unique_id',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'approval_chain',
            'status',
            'unique_id',
            'created_at',
        ]

    def validate(self, data):
        """
        Custom validation for Minute data.
        Ensures title and subject are provided when submitting.
        """
        if self.context.get("is_submit", False):  # Context flag to check for submission
            if not data.get("title"):
                raise serializers.ValidationError({"title": "Title is required when submitting the minute."})
            if not data.get("subject"):
                raise serializers.ValidationError({"subject": "Subject is required when submitting the minute."})
        return data


class MinuteApprovalSerializer(serializers.ModelSerializer):
    """
    Serializer for the MinuteApproval model.
    Handles the approval process with detailed information.
    """
    approver = serializers.StringRelatedField(read_only=True)
    minute = serializers.StringRelatedField(read_only=True)
    approval_chain = serializers.StringRelatedField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = MinuteApproval
        fields = [
            'id',
            'minute',
            'approval_chain',
            'approver',
            'status',
            'status_display',
            'action',
            'remarks',
            'action_time',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'minute',
            'approval_chain',
            'approver',
            'status_display',
            'created_at',
            'updated_at',
            'action_time',
        ]

    def validate_status(self, value):
        """
        Validates the status to ensure consistency during approval actions.
        """
        if value not in ['Pending', 'Approved', 'Rejected', 'Marked', 'Returned']:
            raise serializers.ValidationError(f"Invalid status: {value}.")
        return value


class ApproverSerializer(serializers.ModelSerializer):
    """
    Serializer for the Approver model.
    Displays user details and order in the chain.
    """
    user = serializers.StringRelatedField()

    class Meta:
        model = Approver
        fields = [
            'id',
            'user',
            'order',
            'status',
        ]


class ApprovalChainSerializer(serializers.ModelSerializer):
    """
    Serializer for the ApprovalChain model.
    Includes nested approvers for detailed views.
    """
    approvers = ApproverSerializer(source='approvers', many=True, read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = ApprovalChain
        fields = [
            'id',
            'name',
            'approvers',
            'created_by',
            'status',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'status',
            'created_at',
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    Displays user details for dropdowns or related fields.
    """
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
        ]
