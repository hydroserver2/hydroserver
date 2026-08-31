import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class ObservedProperty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="observed_properties",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    definition = models.TextField(null=True, blank=True)
    description = models.TextField()
    type = models.CharField(max_length=500)
    code = models.CharField(max_length=500)

    def __str__(self):
        return f"{self.name} — {self.id}"

    class Meta:
        verbose_name_plural = "Observed properties"


class VariableType(models.Model):
    name = models.CharField(max_length=255, unique=True)
