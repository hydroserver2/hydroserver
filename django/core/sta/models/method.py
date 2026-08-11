import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class Method(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="methods",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=100)
    description = models.TextField()
    definition = models.CharField(max_length=500, blank=True, null=True)
    sensor_model = models.CharField(max_length=255, null=True, blank=True)
    sensor_model_manufacturer = models.CharField(
        max_length=255, null=True, blank=True
    )
    sensor_model_definition = models.CharField(
        max_length=500, null=True, blank=True
    )

    def __str__(self):
        return f"{self.name} — {self.id}"


class MethodType(models.Model):
    name = models.CharField(max_length=255, unique=True)
