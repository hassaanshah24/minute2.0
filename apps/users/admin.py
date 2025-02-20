# apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from .models import CustomUser
from apps.departments.models import Department

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for the CustomUser model with integration of Department.
    """
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'department', 'designation', 'employee_id', 'phone_number'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'department', 'designation', 'employee_id', 'phone_number'),
        }),
    )

    list_display = ['username', 'email', 'role', 'department', 'designation', 'employee_id', 'is_staff']
    list_filter = ['role', 'department']

    search_fields = ['username', 'email', 'department__name', 'employee_id']

    autocomplete_fields = ['department']  # Enables autocomplete for departments

    def save_model(self, request, obj, form, change):
        """
        Override save_model to ensure the uniqueness of employee_id and handle custom logic.
        """
        if not change and obj.employee_id and CustomUser.objects.filter(employee_id=obj.employee_id).exists():
            raise ValidationError("A user with this Employee ID already exists.")
        obj.clean()  # Ensure model validation.
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """
        Customize queryset to prefetch related departments for performance optimization.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('department')
