import uuid6

from django.db import models

from .session import QCSession


class OperationType(models.TextChoices):
    SELECTION = "SELECTION"
    VALUE_THRESHOLD = "VALUE_THRESHOLD"
    DATETIME_RANGE = "DATETIME_RANGE"
    CHANGE = "CHANGE"
    RATE_OF_CHANGE = "RATE_OF_CHANGE"
    FIND_GAPS = "FIND_GAPS"
    PERSISTENCE = "PERSISTENCE"
    ADD_POINTS = "ADD_POINTS"
    CHANGE_VALUES = "CHANGE_VALUES"
    ASSIGN_VALUES_BULK = "ASSIGN_VALUES_BULK"
    DELETE_POINTS = "DELETE_POINTS"
    DRIFT_CORRECTION = "DRIFT_CORRECTION"
    INTERPOLATE = "INTERPOLATE"
    SHIFT_DATETIMES = "SHIFT_DATETIMES"
    FILL_GAPS = "FILL_GAPS"
    ASSIGN_DATETIMES_BULK = "ASSIGN_DATETIMES_BULK"


class QCOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    session = models.ForeignKey(QCSession, on_delete=models.CASCADE, related_name="operations")
    order = models.PositiveIntegerField()
    operation_type = models.CharField(max_length=30, choices=OperationType)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)
    arguments = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "quality"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["session", "order"], name="unique_qc_operation_order_per_session")
        ]

    def __str__(self):
        return f"{self.session_id} - {self.order} ({self.operation_type})"
