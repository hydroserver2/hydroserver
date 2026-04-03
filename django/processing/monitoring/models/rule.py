import uuid6

from django.db import models

from core.sta.models import Datastream
from processing.monitoring.models.task import MonitoringTask


class RuleType(models.TextChoices):
    ALLOWED_RANGE = "range"
    RATE_OF_CHANGE = "rate_of_change"
    PERSISTENCE = "persistence"
    MISSING_DATA = "missing_data"


class WindowUnits(models.TextChoices):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class MonitoredDatastream(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(
        MonitoringTask,
        on_delete=models.CASCADE,
        related_name="monitored_datastreams",
    )
    datastream = models.ForeignKey(
        Datastream,
        on_delete=models.CASCADE,
        related_name="monitoring",
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "monitoring"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "datastream"],
                name="unique_monitored_datastream_per_task",
            )
        ]

    def __str__(self):
        return f"{self.task} - {self.datastream}"


class MonitoringRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    monitored_datastream = models.ForeignKey(
        MonitoredDatastream,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    rule_type = models.CharField(max_length=255, choices=RuleType)

    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)

    max_change = models.FloatField(null=True, blank=True)
    max_persistence_count = models.IntegerField(null=True, blank=True)

    window = models.IntegerField(null=True, blank=True)
    window_units = models.CharField(
        max_length=255, choices=WindowUnits, null=True, blank=True
    )

    class Meta:
        app_label = "monitoring"
        constraints = [
            models.UniqueConstraint(
                fields=["monitored_datastream", "rule_type"],
                name="unique_monitoring_rule_type_per_datastream",
            )
        ]

    def __str__(self):
        return f"{self.monitored_datastream} - {self.rule_type}"
