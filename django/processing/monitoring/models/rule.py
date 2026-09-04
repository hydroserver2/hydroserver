import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

from core.sta.models import Datastream
from processing.monitoring.models.task import MonitoringTask


class RuleType(models.TextChoices):
    ALLOWED_RANGE = "range"
    RATE_OF_CHANGE = "rate_of_change"
    PERSISTENCE = "persistence"
    MISSING_DATA = "missing_data"


class WindowIntervalUnits(models.TextChoices):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class MonitoringRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    task = models.ForeignKey(
        MonitoringTask,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    datastream = models.ForeignKey(
        Datastream,
        on_delete=models.CASCADE,
        related_name="monitoring_rules",
    )
    rule_type = models.CharField(max_length=255, choices=RuleType)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    window_interval = models.IntegerField(null=True, blank=True)
    window_interval_units = models.CharField(max_length=255, choices=WindowIntervalUnits, null=True, blank=True)

    class Meta:
        app_label = "monitoring"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "datastream", "rule_type"],
                name="unique_monitoring_rule_type_per_datastream_task",
            )
        ]

    def __str__(self):
        return f"{self.task} - {self.datastream} - {self.rule_type}"

    def clean(self):
        if not self.datastream_id or not self.task_id:
            return

        try:
            datastream_site_id = self.datastream.monitoring_site_id
        except ObjectDoesNotExist:
            return

        try:
            task_site_id = self.task.monitoring_site_id
        except ObjectDoesNotExist:
            return

        if datastream_site_id != task_site_id:
            raise ValidationError("The datastream must belong to the same monitoring site as this task.")

        has_min = self.min_value is not None
        has_max = self.max_value is not None
        has_window = self.window_interval is not None
        has_window_units = self.window_interval_units is not None

        if has_window != has_window_units:
            raise ValidationError("window_interval and window_interval_units must both be set or both be omitted.")

        if self.rule_type == RuleType.ALLOWED_RANGE:
            if not has_min and not has_max:
                raise ValidationError("At least one of min_value or max_value is required for rule_type 'range'.")
            if has_min and has_max and self.min_value >= self.max_value:
                raise ValidationError("min_value must be less than max_value.")
            if has_window:
                raise ValidationError("window_interval must not be set for rule_type 'range'.")

        elif self.rule_type == RuleType.RATE_OF_CHANGE:
            if not has_max:
                raise ValidationError("max_value is required for rule_type 'rate_of_change'.")
            if not has_window:
                raise ValidationError(
                    "window_interval and window_interval_units are required for rule_type 'rate_of_change'."
                )
            if has_min:
                raise ValidationError("min_value must not be set for rule_type 'rate_of_change'.")

        elif self.rule_type == RuleType.PERSISTENCE:
            if not has_window:
                raise ValidationError(
                    "window_interval and window_interval_units are required for rule_type 'persistence'."
                )
            if has_min and has_max and self.min_value >= self.max_value:
                raise ValidationError("min_value must be less than max_value.")

        elif self.rule_type == RuleType.MISSING_DATA:
            if not has_window:
                raise ValidationError(
                    "window_interval and window_interval_units are required for rule_type 'missing_data'."
                )
            if has_min or has_max:
                raise ValidationError("min_value and max_value must not be set for rule_type 'missing_data'.")
