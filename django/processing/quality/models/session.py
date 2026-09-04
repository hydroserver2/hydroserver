import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q

from .history import QCHistory


class SessionStatus(models.TextChoices):
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"


class QCSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
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

    def clean(self):
        if self.phenomenon_time_start and self.phenomenon_time_end:
            if self.phenomenon_time_end <= self.phenomenon_time_start:
                raise ValidationError("phenomenon_time_end must be after phenomenon_time_start.")

        if not self._state.adding:
            original = QCSession.objects.filter(pk=self.pk).only("status").first()
            if original and original.status == SessionStatus.COMMITTED:
                raise ValidationError("Committed sessions cannot be modified.")

        if not self.history_id:
            return

        try:
            source_datastream = self.history.source_datastream
        except ObjectDoesNotExist:
            return

        if source_datastream is None:
            raise ValidationError("This history has no source datastream.")

        if (
            source_datastream.phenomenon_end_time is not None
            and self.phenomenon_time_end is not None
            and self.phenomenon_time_end > source_datastream.phenomenon_end_time
        ):
            raise ValidationError(
                "phenomenon_time_end cannot extend past the source datastream's current end time."
            )


class QCSessionDependency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    session = models.ForeignKey(QCSession, on_delete=models.CASCADE, related_name="dependencies")
    dependency = models.ForeignKey(QCSession, on_delete=models.CASCADE, related_name="dependents")

    class Meta:
        app_label = "quality"
        constraints = [
            models.UniqueConstraint(fields=["session", "dependency"], name="unique_qc_session_dependency")
        ]

    def __str__(self):
        return f"{self.session_id} depends on {self.dependency_id}"
