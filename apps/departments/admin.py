from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department', 'dean', 'created_by', 'created_at', 'updated_at')
    search_fields = ('name', 'code', 'head_of_department__username', 'dean__username')
    list_filter = ('created_at', 'updated_at', 'head_of_department', 'dean')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ("Basic Information", {
            'fields': ('name', 'description', 'code', 'head_of_department', 'dean')
        }),
        ("Metadata", {
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Assign created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
