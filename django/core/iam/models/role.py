import uuid

from django.db import models
from django.db.models import Q

from ..permissions.registry import register_resource_type
from .workspace import Workspace


@register_resource_type()
class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="roles",
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(workspace__isnull=True),
                name="unique_global_role_name",
            ),
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(workspace__isnull=False),
                name="unique_workspace_role_name",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.id}"
