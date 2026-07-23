import uuid

from django.db import models

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


@register_resource_type(privacy_chain=["workspace__is_private"])
class ResultQualifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="result_qualifiers",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return f"{self.code} — {self.id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "workspace_id"],
                name="unique_scoped_result_qualifier_code",
                nulls_distinct=False,
            ),
        ]
