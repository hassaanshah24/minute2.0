from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    MinuteAPIView,
    ApprovalChainAPIView,
    UpdateMinuteStatusAPIView,
    SubmitMinuteAPIView,
)

urlpatterns = [
    # Authentication Endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Minute APIs
    path('minute/', MinuteAPIView.as_view(), name='minute-api-create'),  # Create a new minute
    path('minute/<int:minute_id>/', MinuteAPIView.as_view(), name='minute-api-detail'),  # Retrieve a specific minute

    # Approval Chain APIs
    path('approval-chain/', ApprovalChainAPIView.as_view(), name='approval-chain-api-create'),  # Create an approval chain
    path('approval-chain/<int:chain_id>/', ApprovalChainAPIView.as_view(), name='approval-chain-api-detail'),  # Retrieve an approval chain

    # Submit API
    path('minute/submit/', SubmitMinuteAPIView.as_view(), name='minute-submit'),  # Submit a minute

    # Update Status API
    path('minute/status/update/<int:minute_id>/', UpdateMinuteStatusAPIView.as_view(), name='minute-status-update'),  # Update minute status
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
