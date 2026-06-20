from django.apps import AppConfig
from django.template.defaulttags import register


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "attendance"


@register.filter
def get_item(mapping, key):
    """Template helper to access dict items safely."""
    return mapping.get(key)

