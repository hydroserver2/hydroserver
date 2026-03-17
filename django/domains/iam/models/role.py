import uuid6
import typing
from typing import Literal, Optional
from django.db import models
from django.db.models import Q
from .workspace import Workspace
from .utils import PermissionChecker

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class RoleQueryset(models.QuerySet):
    def visible(self, principal: Optional["User"]):
        if principal is None:
            return self.filter(
                Q(workspace__isnull=True) | Q(workspace__is_private=False)
            )
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(workspace__isnull=True)
                    | Q(workspace__is_private=False)
                    | Q(workspace__owner=principal)
                    | Q(
                        workspace__collaborators__user=principal,
                        workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Role",
                        ],
                        workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        else:
            return self.filter(
                Q(workspace__isnull=True) | Q(workspace__is_private=False)
            )


class Role(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    workspace = models.ForeignKey(
        "Workspace",
        on_delete=models.DO_NOTHING,
        related_name="roles",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_user_role = models.BooleanField(default=True)
    is_apikey_role = models.BooleanField(default=False)

    objects = RoleQueryset.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(cls, principal: Optional["User"], workspace: Workspace):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="Role"
        )

    def get_principal_permissions(
        self, principal: Optional["User"]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal, workspace=self.workspace, resource_type="Role"
        )

        return permissions

    def delete(self, *args, **kwargs):
        self.delete_contents(filter_arg=self, filter_suffix="")
        super().delete(*args, **kwargs)

    @staticmethod
    def delete_contents(filter_arg: models.Model, filter_suffix: Optional[str]):
        from domains.iam.models import Permission, Collaborator, APIKey

        role_relation_filter = f"role__{filter_suffix}" if filter_suffix else "role"

        APIKey.objects.filter(**{role_relation_filter: filter_arg}).delete()
        Collaborator.objects.filter(**{role_relation_filter: filter_arg}).delete()
        Permission.objects.filter(**{role_relation_filter: filter_arg}).delete()
