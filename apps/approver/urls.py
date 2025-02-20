from django.urls import path
from .views.dashboard import dashboard
from .views.minute_details import minute_details
from .views.pending_minutes import pending_minutes
from .views.actions import approve_minute, reject_minute, mark_to_minute, return_to_minute, process_action
from .views.track_admin_minute import track_admin_minute  # Admin's Track Minute
from .views.approval_tracker import approval_tracker
from .views.department_archive import department_archive  # Import the Department Archive view

app_name = 'approver'

urlpatterns = [
    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),

    # Minute Details
    path('minute/<int:pk>/', minute_details, name='minute_details'),

    # Pending Minutes
    path('pending_minutes/', pending_minutes, name='pending_minutes'),

    # Approver Actions
    path('minute/<int:pk>/approve/', approve_minute, name='approve_minute'),
    path('minute/<int:pk>/reject/', reject_minute, name='reject_minute'),
    path('minute/<int:pk>/mark-to/', mark_to_minute, name='mark_to_minute'),
    path('minute/<int:pk>/return-to/', return_to_minute, name='return_to_minute'),

    # Unified Action Processing
    path('minute/<int:pk>/process-action/', process_action, name='process_action'),

    # Admin Track Minute (unique to admin)
    path('minute/admin-track/<int:pk>/', track_admin_minute, name='track_admin_minute'),

    # Approval Tracker
    path('approval-tracker/', approval_tracker, name='approval_tracker'),

    # Department Archive (new)
    path('department-archive/', department_archive, name='department_archive'),
]
