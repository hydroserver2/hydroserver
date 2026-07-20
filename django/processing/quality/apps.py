from django.apps import AppConfig


class QualityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "processing.quality"
    label = "quality"
    verbose_name = "Quality Control"
