import re
import uuid
import jmespath as jmespath_lib
import pytz

from datetime import datetime
from jmespath.exceptions import JMESPathError

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask

from core.iam.models import Workspace
from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type


_UTC_OFFSET_RE = re.compile(r"^[+-](\d{4}|\d{2}:\d{2})$")


def _validate_utc_offset(value: str) -> None:
    """
    Native port of hydroserverpy.etl.models.timestamp.Timezone._validate_utc_offset
    - kept in sync manually since models must not import hydroserverpy.
    """

    if not _UTC_OFFSET_RE.match(value):
        raise ValueError(
            f"Invalid timestamp UTC offset '{value}'. "
            "UTC offsets must be specified in ±HHMM or ±HH:MM format (e.g: '-0700' or '-07:00') "
            "with hours between 00 and 14 and minutes between 00 and 59."
        )

    clean = value.replace(":", "")
    hours = int(clean[1:3])
    minutes = int(clean[3:5])

    if hours > 14 or minutes >= 60 or (hours == 14 and minutes != 0):
        raise ValueError(
            f"Invalid timestamp UTC offset '{value}'. "
            "UTC offsets must be specified in ±HHMM or ±HH:MM format (e.g: '-0700' or '-07:00') "
            "with hours between 00 and 14 and minutes between 00 and 59."
        )


class TimezoneType(models.TextChoices):
    OFFSET = "offset"
    IANA = "iana"


class PlaceholderVariableType(models.TextChoices):
    RUN_TIME = "run_time"
    LATEST_OBSERVATION_TIMESTAMP = "latest_observation_timestamp"
    PER_TASK = "per_task"
    DATA_INGESTION_WINDOW_START = "window_start"
    DATA_INGESTION_WINDOW_END = "window_end"


class DataIngestionWindowAnchorType(models.TextChoices):
    LATEST_OBSERVATION_TIMESTAMP = "latest_observation_timestamp"
    RUN_TIME = "run_time"
    FIXED_TIMESTAMP = "fixed_timestamp"


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

    def clean(self):
        if (self.auth_header_name is None) != (self.auth_header_value is None):
            raise ValidationError(
                "auth_header_name and auth_header_value must both be provided or both be omitted."
            )

        if self.timezone_type in (TimezoneType.OFFSET, TimezoneType.IANA) and not self.timezone:
            raise ValidationError(
                "timezone is required when timezone_type is 'offset' or 'iana'."
            )
        elif self.timezone_type == TimezoneType.OFFSET:
            try:
                _validate_utc_offset(self.timezone)
            except ValueError as e:
                raise ValidationError(str(e)) from e
        elif self.timezone_type == TimezoneType.IANA:
            if self.timezone not in pytz.all_timezones_set:
                raise ValidationError(
                    f"Unknown timezone '{self.timezone}'. "
                    "Provide a valid IANA timezone name (e.g. 'America/Denver')."
                )
        elif not self.timezone_type and self.timezone:
            raise ValidationError(
                "timezone must not be set when timezone_type is not provided."
            )


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
        constraints = [
            models.UniqueConstraint(
                fields=["data_connection", "name", "variable_type"],
                name="unique_placeholder_variable_name_and_type_per_data_connection",
                violation_error_message=(
                    "A placeholder variable with this name and type already exists on this data connection."
                ),
            )
        ]

    def clean(self):
        if self.timestamp_format:
            if self.variable_type not in (
                PlaceholderVariableType.RUN_TIME, PlaceholderVariableType.LATEST_OBSERVATION_TIMESTAMP
            ):
                raise ValidationError(
                    "timestamp_format is only allowed on 'run_time' and 'latest_observation_timestamp' "
                    "placeholder variables."
                )
            try:
                datetime(2000, 1, 1).strftime(self.timestamp_format)
            except Exception as e:
                raise ValidationError(
                    f"Invalid timestamp format string {self.timestamp_format!r}. "
                    "Ensure the string uses valid strftime directives (e.g., '%Y-%m-%d %H:%M:%S')."
                ) from e


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

    # Data ingestion window fields
    data_ingestion_window_start_anchor = models.CharField(
        max_length=255, choices=DataIngestionWindowAnchorType, null=True, blank=True
    )
    data_ingestion_window_start_lookback = models.PositiveIntegerField(null=True, blank=True)
    data_ingestion_window_start_lookback_unit = models.CharField(max_length=255, null=True, blank=True)
    data_ingestion_window_start_timestamp = models.DateTimeField(null=True, blank=True)
    data_ingestion_window_end_anchor = models.CharField(
        max_length=255, choices=DataIngestionWindowAnchorType, null=True, blank=True
    )
    data_ingestion_window_end_lookback = models.PositiveIntegerField(null=True, blank=True)
    data_ingestion_window_end_lookback_unit = models.CharField(max_length=255, null=True, blank=True)
    data_ingestion_window_end_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "etl"

    def clean(self):
        if self.payload_type == PayloadType.CSV:
            missing = [
                field for field in ("header_row", "data_start_row", "delimiter")
                if not getattr(self, field)
            ]
            if missing:
                raise ValidationError(f"{', '.join(missing)} required for CSV payloads.")

        elif self.payload_type == PayloadType.JSON:
            if not self.jmespath:
                raise ValidationError("jmespath is required for JSON payloads.")

        if self.jmespath:
            try:
                jmespath_lib.compile(self.jmespath)
            except JMESPathError as e:
                raise ValidationError(f"Invalid JMESPath expression: {e}") from e

        if self.timestamp_format:
            try:
                datetime(2000, 1, 1).strftime(self.timestamp_format)
            except Exception as e:
                raise ValidationError(
                    f"Invalid timestamp format string {self.timestamp_format!r}. "
                    "Ensure the string uses valid strftime directives (e.g., '%Y-%m-%d %H:%M:%S')."
                ) from e


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

    def clean(self):
        if not self.periodic_task_id:
            raise ValidationError("A schedule is required when recipient emails are provided.")

        if not self.recipients.exists():
            raise ValidationError("At least one recipient email is required.")


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
