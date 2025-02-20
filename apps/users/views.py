from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import ProfileUpdateForm
from apps.departments.models import Department


class LoginView(BaseLoginView):
    template_name = "users/login.html"  # Use a custom login template


class LogoutView(BaseLogoutView):
    next_page = '/'  # Redirect to the home page or login page after logout


class FacultyDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard_faculty.html"


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard_admin.html"


class SuperuserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard_superuser.html"


@login_required
def role_based_redirect_view(request):
    """
    Redirect users to their role-based dashboard after login.
    """
    if request.user.is_superuser:
        return redirect(reverse('users:superuser_dashboard'))
    elif request.user.role == 'Faculty':
        return redirect(reverse('users:faculty_dashboard'))
    elif request.user.role == 'Admin':
        return redirect(reverse('users:admin_dashboard'))
    return redirect('/')



@login_required
def profile_view(request):
    """
    Display user profile.
    """
    return render(request, 'users/profile_view.html', {'user': request.user})

@login_required
def profile_edit_view(request):
    """
    Edit user profile.
    """
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')  # Redirect to profile after saving
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'users/profile_edit.html', {'form': form, 'user': user})