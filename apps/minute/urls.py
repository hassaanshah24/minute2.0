from django.urls import path
from . import views

app_name = 'minute'

urlpatterns = [
    # Create or edit a minute
    path('create/', views.CreateMinuteView.as_view(), name='create'),

    # Track all submitted minutes
    path('track/', views.TrackMinuteView.as_view(), name='track'),

    # Track a specific minute
    path('track/<int:pk>/', views.TrackMinuteDetailView.as_view(), name='track_detail'),

    # Submission success page
    path('submit_success/<int:minute_id>/', views.SubmitMinuteSuccessView.as_view(), name='submit_success'),

    # Archived minutes
    path('archive/', views.ArchiveView.as_view(), name='archive'),

    # Approval chain status API
    path('api/approval_status/<int:minute_id>/', views.ApprovalChainStatusView.as_view(), name='approval_status'),

    # Preview the formatted minute sheet
    path('preview/<int:minute_id>/', views.preview_minute_sheet, name='preview_minute'),

    # 📌 New: Generate & Download PDF of Minute Sheet
    path('minute/<int:minute_id>/pdf/', views.GenerateMinutePDFView.as_view(), name='minute_pdf'),
]
