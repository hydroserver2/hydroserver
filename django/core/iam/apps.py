from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.iam"
    label = "iam"
    verbose_name = "Identity and Access Management"

    def ready(self):
        import core.iam.signals  # noqa: F401
