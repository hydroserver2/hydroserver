import uuid

from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class UnitType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="unit_types",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    search_vector = SearchVectorField(null=True, editable=False)

    def __str__(self):
        return f"{self.name} — {self.id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "workspace_id"],
                name="unique_scoped_unit_type_name",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            GinIndex(fields=["search_vector"], name="sta_unittype_search_gin"),
        ]
