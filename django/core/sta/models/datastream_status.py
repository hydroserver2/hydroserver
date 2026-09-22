import uuid

from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

from core.iam.permissions.registry import register_resource_type


@register_resource_type(workspace_field=None)
class DatastreamStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    search_vector = SearchVectorField(null=True, editable=False)

    def __str__(self):
        return f"{self.name} — {self.id}"

    class Meta:
        verbose_name_plural = "Datastream statuses"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="unique_datastream_status_name",
            ),
        ]
        indexes = [
            GinIndex(fields=["search_vector"], name="sta_dsstatus_search_gin"),
        ]
