import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class ProcessingLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="processing_levels",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField()
    definition = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} — {self.id}"
