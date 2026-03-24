from django.apps import AppConfig


class StaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.sta"
    label = "sta"
    verbose_name = "Measurement Data"

    def ready(self):
        import core.sta.signals  # noqa: F401
