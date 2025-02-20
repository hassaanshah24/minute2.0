from django.contrib import admin
from .models import ApprovalChain, Approver
from django.apps import apps

@admin.register(ApprovalChain)
class ApprovalChainAdmin(admin.ModelAdmin):
    """
    Admin view for ApprovalChain.
    Displays key details and restricts certain actions to ensure chains are managed via the app.
    """
    list_display = ('name', 'created_by', 'created_at', 'status')
    search_fields = ('name', 'created_by__username')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)  # Newer chains appear first

    fieldsets = (
        ("Approval Chain Details", {
            "fields": ("name", "created_by", "status", "created_at"),
        }),
    )

    readonly_fields = ('created_at', 'status')

    def has_add_permission(self, request):
        """
               Allow deletion only for superusers or specific conditions.
               """
        return False # Only superusers can delete chains

    def has_delete_permission(self, request, obj=None):
        """
               Allow deletion only for superusers or specific conditions.
               """
        return request.user.is_superuser  # Only superusers can delete chains

@admin.register(Approver)
class ApproverAdmin(admin.ModelAdmin):
    """
    Admin view for Approver.
    Displays approver details and ensures they are managed only via the app.
    """
    list_display = ('approval_chain', 'user', 'order', 'status', 'is_current', 'action_time', 'get_remarks')
    search_fields = ('approval_chain__name', 'user__username')
    list_filter = ('status', 'is_current', 'action_time')
    ordering = ('approval_chain', 'order')  # Sort approvers by chain and their order

    fieldsets = (
        ("Approver Details", {
            "fields": ("approval_chain", "user", "order"),
        }),
        ("Approval Status", {
            "fields": ("status", "is_current", "action_time"),
        }),
    )

    readonly_fields = ('action_time', 'is_current')

    def get_remarks(self, obj):
        MinuteApproval = apps.get_model('minute', 'MinuteApproval')
        approval = MinuteApproval.objects.filter(approval_chain=obj.approval_chain, approver=obj.user).first()
        return approval.remarks if approval else "No remarks"

    get_remarks.short_description = "Remarks"
    def has_add_permission(self, request):
        """
        Restrict adding Approvers via the admin panel.
        Approvers should be managed through the app to ensure correct sequence and logic.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
               Allow deletion only for superusers or specific conditions.
               """
        return request.user.is_superuser  # Only superusers can delete chains
