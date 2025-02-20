from django import template

register = template.Library()

@register.filter
def dict_key(value, key):
    """Fetch the value from a dictionary using a key."""
    return value.get(key, [])
