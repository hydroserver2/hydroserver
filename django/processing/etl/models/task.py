import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type
from core.sta.models import Datastream
from processing.orchestration.models.task import Task

from .data_connection import DataConnection


@register_resource_type(workspace_field="data_connection__workspace")
class EtlTask(Task, ResourcePermissionMixin):
    data_connection = models.ForeignKey(
        DataConnection,
        on_delete=models.CASCADE,
        related_name="etl_tasks",
    )
    task_variables = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} - {self.id}"

    class Meta:
        app_label = "etl"

    @property
    def workspace(self):
        return self.data_connection.workspace


class EtlMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    etl_task = models.ForeignKey(EtlTask, on_delete=models.CASCADE, related_name="etl_mappings")
    source_identifier = models.CharField(max_length=255)
    target_datastream = models.ForeignKey(Datastream, on_delete=models.CASCADE, related_name="etl_mappings")

    class Meta:
        app_label = "etl"
        constraints = [
            models.UniqueConstraint(
                fields=["target_datastream"],
                name="unique_etl_mapping_target_datastream",
                violation_error_message="This datastream is already mapped to by another task.",
            )
        ]

    def clean(self):
        if not self.target_datastream_id or not self.etl_task_id:
            return

        try:
            datastream_workspace_id = self.target_datastream.monitoring_site.workspace_id
        except ObjectDoesNotExist:
            return

        try:
            task_workspace_id = self.etl_task.data_connection.workspace_id
        except ObjectDoesNotExist:
            return

        if datastream_workspace_id != task_workspace_id:
            raise ValidationError(
                "The target datastream must belong to the same workspace as this task."
            )
