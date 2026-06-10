import uuid6

from django.conf import settings
from django.db import models
from django.db.models import Q

from .history import QCHistory


class SessionStatus(models.TextChoices):
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"


class QCSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    history = models.ForeignKey(QCHistory, on_delete=models.CASCADE, related_name="sessions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="qc_sessions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    phenomenon_time_start = models.DateTimeField()
    phenomenon_time_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=SessionStatus, default=SessionStatus.IN_PROGRESS)
    committed_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    source_checksum = models.CharField(max_length=64)
    managed_checksum = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        app_label = "quality"
        ordering = ["phenomenon_time_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["history"],
                condition=Q(status=SessionStatus.IN_PROGRESS),
                name="unique_in_progress_session_per_history",
            )
        ]

    def __str__(self):
        return f"{self.history_id} - {self.id} ({self.status})"


class QCSessionDependency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    session = models.ForeignKey(QCSession, on_delete=models.CASCADE, related_name="dependencies")
    dependency = models.ForeignKey(QCSession, on_delete=models.CASCADE, related_name="dependents")

    class Meta:
        app_label = "quality"
        constraints = [
            models.UniqueConstraint(fields=["session", "dependency"], name="unique_qc_session_dependency")
        ]

    def __str__(self):
        return f"{self.session_id} depends on {self.dependency_id}"
