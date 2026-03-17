import typing
from typing import Literal, Optional
from django.db import models
from django.db.models import Q
from django.conf import settings
from .utils import PermissionChecker

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import Workspace

    User = get_user_model()


class CollaboratorQueryset(models.QuerySet):
    def visible(self, principal: Optional["User"]):
        if principal is None:
            return self.filter(Q(workspace__is_private=False))
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(workspace__is_private=False)
                    | Q(workspace__owner=principal)
                    | Q(
                        workspace__collaborators__user=principal,
                        workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Collaborator",
                        ],
                        workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        else:
            return self.filter(Q(workspace__is_private=False))


class Collaborator(models.Model, PermissionChecker):
    workspace = models.ForeignKey(
        "Workspace", on_delete=models.DO_NOTHING, related_name="collaborators"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="workspace_roles",
    )
    role = models.ForeignKey(
        "Role", on_delete=models.DO_NOTHING, related_name="collaborator_assignments"
    )

    objects = CollaboratorQueryset.as_manager()

    @classmethod
    def can_principal_create(cls, principal: Optional["User"], workspace: "Workspace"):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="Collaborator"
        )

    def get_principal_permissions(
        self, principal: Optional["User"]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal, workspace=self.workspace, resource_type="Collaborator"
        )

        return permissions

    class Meta:
        unique_together = ("user", "workspace")
