import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from domains.iam.models import APIKey, Role
from interfaces.api.schemas.role import RoleOrderByFields, RoleSummaryResponse, RoleDetailResponse
from interfaces.api.service import ServiceUtils

User = get_user_model()


class RoleService(ServiceUtils):
    def get_role_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        try:
            role = Role.objects
            if expand_related:
                role = self.select_expanded_fields(role)
            role = role.get(pk=uid)
        except Role.DoesNotExist:
            raise HttpError(404, "Role does not exist")

        role_permissions = role.get_principal_permissions(principal=principal)

        if "view" not in role_permissions:
            raise HttpError(404, "Role does not exist")

        if action not in role_permissions:
            raise HttpError(403, f"You do not have permission to {action} this role")

        return role

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace").prefetch_related("permissions")

    def list(
        self,
        principal: Optional[User | APIKey],
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
            "is_user_role",
            "is_apikey_role",
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
            queryset.visible(principal=principal)
            .prefetch_related("permissions")
            .distinct()
        )

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                RoleDetailResponse.model_validate(role)
                if expand_related
                else RoleSummaryResponse.model_validate(role)
            )
            for role in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        role = self.get_role_for_action(
            principal=principal,
            uid=uid,
            action="view",
            expand_related=expand_related,
        )

        return (
            RoleDetailResponse.model_validate(role)
            if expand_related
            else RoleSummaryResponse.model_validate(role)
        )
