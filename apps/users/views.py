from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import ProfileUpdateForm
from apps.departments.models import Department


class LoginView(BaseLoginView):
    """ Custom Login View with a stylish login template """
    template_name = "users/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('users:redirect_view'))  # Redirect logged-in users to dashboard
        return super().get(request, *args, **kwargs)


class LogoutView(BaseLogoutView):
    """ Logout and redirect users to the landing page """
    next_page = '/'  # Redirect to the landing page after logout


class FacultyDashboardView(LoginRequiredMixin, TemplateView):
    """ Faculty Dashboard """
    template_name = "users/dashboard_faculty.html"


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """ Admin Dashboard """
    template_name = "users/dashboard_admin.html"


class SuperuserDashboardView(LoginRequiredMixin, TemplateView):
    """ Superuser Dashboard """
    template_name = "users/dashboard_superuser.html"


@login_required
def role_based_redirect_view(request):
    """
    Redirect users to their dashboard based on role.
    """
    if request.user.is_superuser:
        return redirect(reverse('users:superuser_dashboard'))
    elif hasattr(request.user, 'role') and request.user.role:
        if request.user.role == 'Faculty':
            return redirect(reverse('users:faculty_dashboard'))
        elif request.user.role == 'Admin':
            return redirect(reverse('users:admin_dashboard'))

    return redirect('/')  # Default to landing page if no role is found


@login_required
def profile_view(request):
    """ Displays the user's profile. """
    return render(request, 'users/profile_view.html', {'user': request.user})


@login_required
def profile_edit_view(request):
    """ Allows users to edit their profile. """
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect(reverse('users:profile'))  # Redirect to profile after saving
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'users/profile_edit.html', {'form': form, 'user': user})


def landing_page(request):
    """
    Landing Page:
    - Redirects authenticated users to their dashboard.
    - Shows the landing page to anonymous users.
    """
    if request.user.is_authenticated:
        return redirect(reverse('users:redirect_view'))
    return render(request, 'users/landing.html')
