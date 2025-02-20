from django.apps import AppConfig


class ApprovalChainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.approval_chain"

def ready(self):
    import apps.approval_chain.signals

