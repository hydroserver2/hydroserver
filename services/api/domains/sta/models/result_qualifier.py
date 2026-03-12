import uuid6
import typing
from typing import Literal, Optional, Union
from django.db import models
from django.db.models import Q
from domains.iam.models import Workspace
from domains.iam.models.utils import PermissionChecker

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import Workspace, APIKey

    User = get_user_model()


class ResultQualifierQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
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
                            "ResultQualifier",
                        ],
                        workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(workspace__isnull=True)
                | Q(workspace__is_private=False)
                | Q(
                    workspace__apikeys=principal,
                    workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "ResultQualifier",
                    ],
                    workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.filter(
                Q(workspace__isnull=True) | Q(workspace__is_private=False)
            )


class ResultQualifier(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        related_name="result_qualifiers",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=255)
    description = models.TextField()

    objects = ResultQualifierQuerySet.as_manager()

    def __str__(self):
        return f"{self.code} - {self.id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "workspace_id"],
                name="unique_scoped_result_qualifier_code",
                nulls_distinct=False,
            ),
        ]

    @classmethod
    def can_principal_create(
        cls,
        principal: Optional[Union["User", "APIKey"]],
        workspace: Optional["Workspace"] = None,
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="ResultQualifier"
        )

    def get_principal_permissions(
        self, principal: Optional[Union["User", "APIKey"]]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal,
            workspace=self.workspace,
            resource_type="ResultQualifier",
        )

        if (not self.workspace or not self.workspace.is_private) and "view" not in list(
            permissions
        ):
            permissions = list(permissions) + ["view"]

        return permissions
