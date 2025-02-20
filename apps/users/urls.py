from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from .views import (
    LoginView,
    FacultyDashboardView,
    AdminDashboardView,
    SuperuserDashboardView,
    role_based_redirect_view,
    profile_view,
    profile_edit_view,
)

app_name = 'users'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),  # Remove next_page here
    path('redirect/', role_based_redirect_view, name='redirect_view'),
    path('dashboard/faculty/', FacultyDashboardView.as_view(), name='faculty_dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/superuser/', SuperuserDashboardView.as_view(), name='superuser_dashboard'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
]

# Add static file handling in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
