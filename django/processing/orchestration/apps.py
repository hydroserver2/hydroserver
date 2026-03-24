from django.apps import AppConfig


class EtlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "processing.orchestration"
    label = "orchestration"
    verbose_name = "Task Orchestration"
