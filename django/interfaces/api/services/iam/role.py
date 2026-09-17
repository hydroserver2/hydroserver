import uuid

from typing import Optional, Literal, get_args
from django.contrib.auth import get_user_model

from core.iam.models import ServiceAccount, Role
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import NotFoundError, PermissionDeniedError
from interfaces.api.schemas import RoleOrderByFields, RoleResponse
from interfaces.api.service import APIService

User = get_user_model()


class RoleAPIService(APIService):
    @staticmethod
    def get_role_for_action(
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
    ):
        queryset = Role.objects.filter(pk=uid).prefetch_related("permissions")
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

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
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

        queryset, meta = self.apply_pagination(queryset, offset, limit)

        return {
            "data": [RoleResponse.model_validate(role) for role in queryset.all()],
            "meta": meta,
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        role = self.get_role_for_action(principal=principal, uid=uid, action="view")

        return {"data": RoleResponse.model_validate(role), "included": {}}
