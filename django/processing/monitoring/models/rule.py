import uuid6

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
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
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
