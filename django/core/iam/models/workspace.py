import uuid
import typing

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

from ..permissions.registry import register_resource_type

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class WorkspaceQuerySet(models.QuerySet):
    def delete(self):
        from core.sta.models import MonitoringSite
        from core.iam.models import ServiceAccount

        ServiceAccount.objects.filter(workspace__in=self).update(
            is_active=False, key_hash=""
        )
        MonitoringSite.objects.filter(workspace__in=self).delete()

        return super().delete()


@register_resource_type(workspace_field=None, privacy_chain=["is_private"])
class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )
    is_private = models.BooleanField(default=False)

    objects = WorkspaceQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} — {self.id}"

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "owner"], name="unique_workspace_name_per_owner"
            )
        ]

    @property
    def transfer(self):
        return getattr(self, "transfer_confirmation", None)

    def clean(self):
        if not self._state.adding:
            original_workspace = Workspace.objects.get(pk=self.pk)
            if original_workspace.owner == self.owner:
                return

        if self.owner.owned_workspace_limit is not None:
            owned_workspace_count = self.owner.owned_workspaces.exclude(
                pk=self.pk
            ).count()
            if owned_workspace_count >= self.owner.owned_workspace_limit:
                raise ValidationError("User has reached their owned workspace limit.")

    def initiate_transfer(self, new_owner: "User"):
        if getattr(self, "transfer_confirmation", None):
            raise ValueError("Workspace transfer is already pending")

        if new_owner == self.owner:
            raise ValueError(
                "New workspace owner cannot be the same as the current owner"
            )

        WorkspaceTransferConfirmation.objects.create(
            workspace=self, new_owner=new_owner
        )

    def accept_transfer(self):
        if not getattr(self, "transfer_confirmation", None):
            raise ValueError("No workspace transfer is pending")

        self.owner = self.transfer_confirmation.new_owner
        self.full_clean()
        self.save()
        self.transfer_confirmation.delete()

    def reject_transfer(self):
        if not getattr(self, "transfer_confirmation", None):
            raise ValueError("No workspace transfer is pending")

        self.transfer_confirmation.delete()


class WorkspaceTransferConfirmation(models.Model):
    workspace = models.OneToOneField(
        Workspace, on_delete=models.CASCADE, related_name="transfer_confirmation"
    )
    new_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Transfer of {self.workspace} to {self.new_owner}"
