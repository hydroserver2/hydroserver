from django.apps import AppConfig


class StaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "domains.sta"
    label = "sta"
    verbose_name = "Measurement Data"
