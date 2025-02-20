from django import template

register = template.Library()

@register.filter
def unread_notifications_count(notifications):
    """
    Custom template filter to count unread notifications.
    """
    return notifications.filter(is_read=False).count()
