import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class Unit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="units",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=255)
    definition = models.TextField()
    unit_type = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} — {self.id}"


class UnitType(models.Model):
    name = models.CharField(max_length=255, unique=True)
