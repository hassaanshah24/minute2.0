from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('apps.users.urls', namespace='users')),
    path('minutes/', include('apps.minute.urls', namespace='minute')),  # Minute app routes
    path('approval-chain/', include('apps.approval_chain.urls', namespace='approval_chain')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('api/', include('apps.api.urls')),
    path('departments/', include('apps.departments.urls', namespace='departments')),
    path('approver/', include('apps.approver.urls', namespace='approver')),

]
# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)