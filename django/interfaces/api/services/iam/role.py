import uuid
from typing import Optional, Literal, get_args
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from core.iam.models import ServiceAccount, Role
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import NotFoundError, PermissionDeniedError
from interfaces.api.schemas import RoleOrderByFields, RoleSummaryResponse, RoleDetailResponse
from interfaces.api.service import APIService

User = get_user_model()


class RoleAPIService(APIService):
    _permission_actions = ("view", "create", "edit", "delete")

    @staticmethod
    def expand_permissions(role: Role) -> list[dict]:
        """
        Permission rows store one boolean flag per action on a single
        resource_type row; PermissionDetailResponse expects one entry per
        (resource, action) pair, so expand the flags into that shape here.
        """

        return [
            {"resource": permission.resource_type, "action": action}
            for permission in role.permissions.all()
            for action in RoleAPIService._permission_actions
            if getattr(permission, f"can_{action}")
        ]

    def serialize_role(self, role: Role, expand_related: Optional[bool]):
        payload = {
            "id": role.id,
            "workspace_id": role.workspace_id,
            "name": role.name,
            "description": role.description,
            "permissions": self.expand_permissions(role),
        }
        if expand_related:
            payload["workspace"] = role.workspace
            return RoleDetailResponse.model_validate(payload)
        return RoleSummaryResponse.model_validate(payload)

    def get_role_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = Role.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        queryset = principal.annotate_permissions(queryset)

        try:
            role = queryset.get()
        except Role.DoesNotExist:
            raise NotFoundError("Role does not exist")

        if not principal.can_view(role):
            raise NotFoundError("Role does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(role):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this role"
            )

        return role

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace").prefetch_related("permissions")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Role.objects

        for field in [
            "workspace_id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(RoleOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        queryset = (
            principal.filter_by_permission(queryset, "can_view")
            .prefetch_related("permissions")
            .distinct()
        )

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            self.serialize_role(role, expand_related) for role in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        role = self.get_role_for_action(
            principal=principal,
            uid=uid,
            action="view",
            expand_related=expand_related,
        )

        return self.serialize_role(role, expand_related)
