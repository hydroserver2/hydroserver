from django.conf import settings
from django.db import models
from django.db.models import Q

from ..permissions.registry import register_resource_type
from .role import Role
from .service_account import ServiceAccount
from .workspace import Workspace


@register_resource_type()
class Collaborator(models.Model):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="collaborators"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="collaborations",
    )
    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="collaborations",
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="collaborator_assignments"
    )

    class Meta:
        verbose_name = "Collaborator"
        verbose_name_plural = "Collaborators"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, service_account__isnull=True) |
                    Q(user__isnull=True, service_account__isnull=False)
                ),
                name="collaborator_principal_is_user_xor_service_account",
            ),
            models.UniqueConstraint(
                fields=["workspace", "user"],
                condition=Q(user__isnull=False),
                name="unique_workspace_user_collaborator",
            ),
            models.UniqueConstraint(
                fields=["workspace", "service_account"],
                condition=Q(service_account__isnull=False),
                name="unique_workspace_service_account_collaborator",
            ),
        ]
