from django.shortcuts import redirect
from django.urls import reverse


class RoleBasedRedirectMiddleware:
    """
    Redirect authenticated users to their respective dashboards based on role.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip API paths
        if request.path.startswith('/api/'):
            return self.get_response(request)

        # Handle role-based redirection for authenticated users
        if request.user.is_authenticated and request.path == '/accounts/profile/':
            if request.user.is_superuser:
                return redirect(reverse('users:superuser_dashboard'))
            elif request.user.role == 'Faculty':
                return redirect(reverse('users:faculty_dashboard'))
            elif request.user.role == 'Admin':
                return redirect(reverse('users:admin_dashboard'))

        return self.get_response(request)
