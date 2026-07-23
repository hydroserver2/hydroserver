import uuid

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask

from core.iam.models import Workspace
from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type


class TimezoneType(models.TextChoices):
    OFFSET = "offset"
    IANA = "iana"


class PlaceholderVariableType(models.TextChoices):
    RUN_TIME = "run_time"
    LATEST_OBSERVATION_TIMESTAMP = "latest_observation_timestamp"
    PER_TASK = "per_task"


@register_resource_type()
class DataConnection(models.Model, ResourcePermissionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    workspace = models.ForeignKey(
        Workspace,
        related_name="data_connections",
        on_delete=models.CASCADE,
    )
    source_url = models.TextField()
    auth_header_name = models.CharField(max_length=255, null=True, blank=True)
    auth_header_value = models.TextField(null=True, blank=True)
    timezone_type = models.CharField(max_length=255, choices=TimezoneType, null=True, blank=True)
    timezone = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        app_label = "etl"

    def __str__(self):
        return f"{self.name} - {self.id}"


class PlaceholderVariable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    data_connection = models.ForeignKey(
        DataConnection,
        on_delete=models.CASCADE,
        related_name="placeholder_variables"
    )
    name = models.CharField(max_length=255)
    variable_type = models.CharField(choices=PlaceholderVariableType, max_length=255)
    timestamp_format = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        app_label = "etl"


class PayloadType(models.TextChoices):
    CSV = "CSV"
    JSON = "JSON"


class PayloadDelimiter(models.TextChoices):
    COMMA = ","
    TAB = "\t"
    SEMICOLON = ";"
    PIPE = "|"
    SPACE = " "


class Payload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    data_connection = models.OneToOneField(
        DataConnection, on_delete=models.CASCADE, related_name="payload"
    )
    payload_type = models.CharField(max_length=255, choices=PayloadType)

    # CSV fields
    header_row = models.IntegerField(null=True, blank=True)
    data_start_row = models.IntegerField(null=True, blank=True)
    delimiter = models.CharField(max_length=1, choices=PayloadDelimiter, null=True, blank=True)

    # JSON fields
    jmespath = models.TextField(null=True, blank=True)

    # Timestamp fields
    timestamp_key = models.CharField(max_length=255)
    timestamp_format = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        app_label = "etl"


class DataConnectionNotification(models.Model):
    data_connection = models.OneToOneField(
        DataConnection,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="notification",
    )
    periodic_task = models.OneToOneField(
        PeriodicTask,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_connection_notification",
    )

    class Meta:
        app_label = "etl"

    def __str__(self):
        return str(self.data_connection_id)


class DataConnectionNotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    notification = models.ForeignKey(
        DataConnectionNotification, on_delete=models.CASCADE, related_name="recipients"
    )
    email = models.EmailField()

    class Meta:
        app_label = "etl"
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "email"],
                name="unique_data_connection_notification_recipient_email",
            )
        ]

    def __str__(self):
        return f"{self.notification_id} — {self.email}"


@receiver(pre_delete, sender=DataConnectionNotification)
def delete_related_periodic_task(sender, instance, **kwargs):
    periodic_task = instance.periodic_task

    if not periodic_task:
        return

    if periodic_task.crontab_id:
        crontab = periodic_task.crontab
        PeriodicTask.objects.filter(pk=periodic_task.pk).update(crontab=None)
        crontab.delete()

    if periodic_task.interval_id:
        interval = periodic_task.interval
        PeriodicTask.objects.filter(pk=periodic_task.pk).update(interval=None)
        interval.delete()

    DataConnectionNotification.objects.filter(pk=instance.pk).update(periodic_task=None)
    periodic_task.delete()
