from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "domains.iam"
    label = "iam"
    verbose_name = "Identity and Access Management"
