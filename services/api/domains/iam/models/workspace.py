import uuid6
import typing
from typing import Literal, Optional
from django.db import models
from django.db.models import Q
from django.conf import settings

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class WorkspaceQueryset(models.QuerySet):
    def get_queryset(self):
        return self.select_related("transfer_confirmation", "delete_confirmation")

    def visible(self, principal: Optional["User"]):
        queryset = self.get_queryset()

        if principal is None:
            return queryset.filter(is_private=False)
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return queryset
            else:
                return queryset.filter(
                    Q(is_private=False)
                    | Q(owner=principal)
                    | Q(collaborators__user=principal)
                    | Q(transfer_confirmation__new_owner=principal)
                )
        elif hasattr(principal, "workspace"):
            return queryset.filter(Q(is_private=False) | Q(pk=principal.workspace.pk))
        else:
            return queryset.filter(is_private=False)

    def associated(self, principal: Optional["User"]):
        queryset = self.get_queryset()

        if principal is None:
            return queryset.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return queryset
            else:
                return queryset.filter(
                    Q(owner=principal)
                    | Q(collaborators__user=principal)
                    | Q(transfer_confirmation__new_owner=principal)
                )
        elif hasattr(principal, "workspace"):
            return queryset.filter(id=principal.workspace.id)
        else:
            return queryset.none()


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    is_private = models.BooleanField(default=False)

    objects = WorkspaceQueryset.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "owner"], name="unique_workspace_name_per_owner"
            )
        ]

    @property
    def link(self):
        return f"{settings.PROXY_BASE_URL}/api/auth/workspaces/{self.id}"

    @property
    def transfer_details(self):
        return getattr(self, "transfer_confirmation", None)

    @property
    def delete_details(self):
        return getattr(self, "delete_confirmation", None)

    @classmethod
    def can_principal_create(cls, principal: Optional["User"]):
        return (
            hasattr(principal, "account_type") and principal.account_type != "limited"
        )

    def get_principal_permissions(
        self, principal: Optional["User"]
    ) -> list[Literal["edit", "delete", "view"]]:
        if hasattr(principal, "account_type"):
            if principal == self.owner or principal.account_type == "admin":
                return ["view", "edit", "delete"]
            elif (
                self.is_private is False
                or self.collaborators.filter(user=principal).exists()
            ):
                return ["view"]
            elif self.transfer_details and self.transfer_details.new_owner == principal:
                return ["view"]
            else:
                return []
        elif hasattr(principal, "workspace"):
            if self.is_private is False or principal.workspace == self:
                return ["view"]
            else:
                return []
        else:
            if self.is_private is False:
                return ["view"]
            else:
                return []

    def delete(self, *args, **kwargs):
        self.delete_contents(filter_arg=self, filter_suffix="")
        super().delete(*args, **kwargs)

    @staticmethod
    def delete_contents(filter_arg: models.Model, filter_suffix: Optional[str]):
        from domains.iam.models import Role, Collaborator, APIKey
        from domains.sta.models import (
            Thing,
            ObservedProperty,
            ProcessingLevel,
            ResultQualifier,
            Sensor,
            Unit,
        )

        workspace_relation_filter = (
            f"workspace__{filter_suffix}" if filter_suffix else "workspace"
        )

        Collaborator.objects.filter(**{workspace_relation_filter: filter_arg}).delete()

        Role.delete_contents(
            filter_arg=filter_arg, filter_suffix=workspace_relation_filter
        )
        Role.objects.filter(**{workspace_relation_filter: filter_arg}).delete()

        APIKey.objects.filter(**{workspace_relation_filter: filter_arg}).delete()

        Thing.delete_contents(
            filter_arg=filter_arg, filter_suffix=workspace_relation_filter
        )
        Thing.objects.filter(**{workspace_relation_filter: filter_arg}).delete()

        ObservedProperty.objects.filter(
            **{workspace_relation_filter: filter_arg}
        ).delete()
        ProcessingLevel.objects.filter(
            **{workspace_relation_filter: filter_arg}
        ).delete()
        ResultQualifier.objects.filter(
            **{workspace_relation_filter: filter_arg}
        ).delete()
        Sensor.objects.filter(**{workspace_relation_filter: filter_arg}).delete()
        Unit.objects.filter(**{workspace_relation_filter: filter_arg}).delete()


class WorkspaceTransferConfirmation(models.Model):
    workspace = models.OneToOneField(
        "Workspace", on_delete=models.CASCADE, related_name="transfer_confirmation"
    )
    new_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    initiated = models.DateTimeField()


class WorkspaceDeleteConfirmation(models.Model):
    workspace = models.OneToOneField(
        "Workspace", on_delete=models.CASCADE, related_name="delete_confirmation"
    )
    initiated = models.DateTimeField()
