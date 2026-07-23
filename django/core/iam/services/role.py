import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from core.iam.models import ServiceAccount, Role
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.schemas import RoleOrderByFields, RoleSummaryResponse, RoleDetailResponse
from core.service import ServiceUtils

User = get_user_model()


class RoleService(ServiceUtils):
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
            raise HttpError(404, "Role does not exist")

        if not principal.can_view(role):
            raise HttpError(404, "Role does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(role):
            raise HttpError(403, f"You do not have permission to {action} this role")

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
            (
                RoleDetailResponse.model_validate(role)
                if expand_related
                else RoleSummaryResponse.model_validate(role)
            )
            for role in queryset.all()
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

        return (
            RoleDetailResponse.model_validate(role)
            if expand_related
            else RoleSummaryResponse.model_validate(role)
        )
