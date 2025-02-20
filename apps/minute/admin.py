from django.contrib import admin
from .models import Minute, MinuteApproval
from .forms import MinuteForm, MinuteApprovalForm
from django.urls import reverse
from django.utils.html import format_html


@admin.register(Minute)
class MinuteAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Minute model.
    """
    list_display = ("title", "created_by", "status", "created_at", "unique_id", "approval_chain_link")
    list_filter = ("status", "created_at", "created_by", "approval_chain")
    search_fields = ("title", "subject", "description", "unique_id", "created_by__username", "approval_chain__name")
    ordering = ("-created_at",)
    readonly_fields = ("unique_id", "created_at", "status", "approval_chain")
    form = MinuteForm

    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "subject", "description", "attachment", "created_by", "approval_chain"),
        }),
        ("Metadata", {
            "fields": ("unique_id", "created_at", "status"),
        }),
    )

    def get_queryset(self, request):
        """
        Optimize queryset to prevent multiple queries when fetching related fields.
        """
        return super().get_queryset(request).select_related("created_by", "approval_chain")

    def approval_chain_link(self, obj):
        """
        Provide a clickable link to the related approval chain in admin.
        """
        if obj.approval_chain:
            url = reverse("admin:approval_chain_approvalchain_change", args=[obj.approval_chain.id])
            return format_html('<a href="{}">{}</a>', url, obj.approval_chain.name)
        return "No Approval Chain"

    approval_chain_link.short_description = "Approval Chain"

    def has_add_permission(self, request):
        """
        Restrict addition of new Minute records via admin.
        """
        return False

    def delete_queryset(self, request, queryset):
        """
        Override delete method to handle cascading deletion of related ApprovalChain.
        """
        for minute in queryset:
            minute.delete()

    def has_change_permission(self, request, obj=None):
        """
        Allow changes only to Draft or Submitted minutes.
        """
        if obj and obj.status not in ['Draft', 'Submitted']:
            return False
        return super().has_change_permission(request, obj)


@admin.register(MinuteApproval)
class MinuteApprovalAdmin(admin.ModelAdmin):
    """
    Admin configuration for the MinuteApproval model.
    """
    list_display = ("minute", "approval_chain", "approver", "status", "action", "action_time", "updated_at")
    list_filter = ("status", "action", "approval_chain", "action_time", "updated_at")
    search_fields = ("minute__title", "approval_chain__name", "approver__username", "remarks")
    ordering = ("-updated_at",)
    readonly_fields = ("minute", "approval_chain", "approver", "action_time", "updated_at")
    form = MinuteApprovalForm

    fieldsets = (
        ("Minute Information", {
            "fields": ("minute", "approval_chain"),
        }),
        ("Approval Details", {
            "fields": ("approver", "action", "status", "remarks", "action_time", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        """
        Optimize queryset to avoid unnecessary queries.
        """
        return super().get_queryset(request).select_related("minute", "approval_chain", "approver")

    def has_add_permission(self, request):
        """
        Restrict addition of new MinuteApproval records via admin.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Restrict changes to MinuteApproval objects to superusers only.
        """
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        """
        Dynamically set readonly fields based on the approval status.
        - Allow remarks to be editable when status is 'Pending', 'Marked', or 'Returned'.
        """
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['Approved', 'Rejected']:
            readonly += ['remarks', 'action']
        return readonly
