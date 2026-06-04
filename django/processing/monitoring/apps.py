from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "processing.monitoring"
    label = "monitoring"
    verbose_name = "Data Quality Monitoring"
