import uuid

from django.db import models

from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type
from core.sta.models import Thing
from processing.orchestration.models.task import Task


@register_resource_type(workspace_field="thing__workspace")
class MonitoringTask(Task, ResourcePermissionMixin):
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="monitoring_tasks",
    )

    class Meta:
        app_label = "monitoring"

    def __str__(self):
        return f"{self.name} - {self.id}"

    @property
    def workspace(self):
        return self.thing.workspace


class MonitoringNotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    task = models.ForeignKey(
        MonitoringTask,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    email = models.EmailField()

    class Meta:
        app_label = "monitoring"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "email"],
                name="unique_monitoring_notification_recipient_email",
            )
        ]

    def __str__(self):
        return f"{self.task_id} — {self.email}"
