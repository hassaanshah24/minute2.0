# departments/dashboard.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Department

@login_required
def department_dashboard(request):
    """
    Dashboard to view all departments and their details.
    Accessible only to superusers.
    """
    if not request.user.is_superuser:
        return render(request, "403.html")  # Optional: Custom 403 template

    departments = Department.objects.all()

    context = {
        "departments": departments,
        "total_departments": departments.count(),
        "department_heads": departments.filter(head_of_department__isnull=False).count(),
    }
    return render(request, "departments/dashboard.html", context)
