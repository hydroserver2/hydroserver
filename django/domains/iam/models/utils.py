import typing
from typing import Optional, Union
from .permission import Permission

if typing.TYPE_CHECKING:
    from domains.iam.models import Workspace, APIKey
    from django.contrib.auth import get_user_model

    User = get_user_model()


class PermissionChecker:
    @classmethod
    def check_create_permissions(
        cls,
        principal: Optional[Union["User", "APIKey"]],
        workspace: Optional["Workspace"],
        resource_type: str,
    ):
        if not principal:
            return False

        if hasattr(principal, "account_type"):
            if principal.account_type in [
                "admin",
                "staff",
            ]:
                if not workspace and resource_type not in [
                    "OrchestrationSystem",
                    "DataConnection",
                    "ProcessingLevel",
                    "Unit",
                    "Sensor",
                    "ResultQualifier",
                    "ObservedProperty",
                ]:
                    return False
                return True

            if not workspace:
                return False

            if workspace.owner == principal:
                return True

            permissions = Permission.objects.filter(
                role__collaborator_assignments__user=principal,
                role__collaborator_assignments__workspace=workspace,
                resource_type__in=["*", resource_type],
            ).values_list("permission_type", flat=True)

        elif hasattr(principal, "workspace"):
            if not workspace or principal.workspace != workspace:
                return False

            permissions = Permission.objects.filter(
                role=principal.role,
                resource_type__in=["*", resource_type],
            ).values_list("permission_type", flat=True)

        else:
            return False

        return any(perm in permissions for perm in ["*", "create"])

    @staticmethod
    def check_object_permissions(
        principal: Optional[Union["User", "APIKey"]],
        workspace: Optional["Workspace"],
        resource_type: str,
    ):
        if not workspace:
            if hasattr(principal, "account_type") and principal.account_type in [
                "admin",
                "staff",
            ]:
                return ["view", "edit", "delete"]
            else:
                return ["view"]

        if hasattr(principal, "account_type"):
            if workspace.owner == principal or principal.account_type in [
                "admin",
                "staff",
            ]:
                return ["view", "edit", "delete"]

            permissions = list(
                Permission.objects.exclude(permission_type="create")
                .filter(
                    role__collaborator_assignments__user=principal,
                    role__collaborator_assignments__workspace=workspace,
                    resource_type__in=["*", resource_type],
                )
                .values_list("permission_type", flat=True)
            )

        elif hasattr(principal, "workspace"):
            if principal.workspace != workspace:
                permissions = []
            else:
                permissions = list(
                    Permission.objects.exclude(permission_type="create")
                    .filter(
                        role=principal.role,
                        resource_type__in=["*", resource_type],
                    )
                    .values_list("permission_type", flat=True)
                )

        else:
            permissions = []

        if "*" in permissions:
            permissions = ["view", "edit", "delete"]

        if not workspace.is_private and "view" not in permissions:
            if resource_type not in [
                "Thing",
                "Datastream",
                "OrchestrationSystem",
                "DataConnection",
                "Task",
                "APIKey",
            ]:
                permissions.append("view")

        return permissions
