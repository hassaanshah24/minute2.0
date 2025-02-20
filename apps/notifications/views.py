from django.views.generic import ListView, UpdateView, View
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.timezone import now
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notification
from django.shortcuts import get_object_or_404

class NotificationListView(LoginRequiredMixin, ListView):
    """
    Display a list of notifications for the logged-in user.
    Shows both read and unread notifications, ordered by creation time.
    """
    model = Notification
    template_name = 'notifications/notifications_list.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        """
        Fetch all notifications for the logged-in user.
        """
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class MarkNotificationAsReadView(LoginRequiredMixin, View):
    """
    Mark a specific notification as read via AJAX.
    """
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=kwargs['pk'], user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True, 'message': 'Notification marked as read.'})

class MarkAllNotificationsAsReadView(LoginRequiredMixin, View):
    """
    Mark all notifications for the logged-in user as read via AJAX.
    """
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True, 'message': 'All notifications marked as read.'})
