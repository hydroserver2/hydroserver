from django.db import models

from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type
from core.sta.models import Thing
from processing.orchestration.models.task import Task


@register_resource_type(workspace_field="thing__workspace")
class DataProductTask(Task, ResourcePermissionMixin):
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="data_product_tasks",
    )

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.name} - {self.id}"

    @property
    def workspace(self):
        return self.thing.workspace
