import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class Sensor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="sensors",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    encoding_type = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    sensor_model = models.CharField(max_length=255, null=True, blank=True)
    sensor_model_link = models.CharField(max_length=500, null=True, blank=True)
    method_type = models.CharField(max_length=100)
    method_link = models.CharField(max_length=500, blank=True, null=True)
    method_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.name} — {self.id}"


class SensorEncodingType(models.Model):
    name = models.CharField(max_length=255, unique=True)


class MethodType(models.Model):
    name = models.CharField(max_length=255, unique=True)
