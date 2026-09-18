import uuid

from typing import Literal, Optional, get_args
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Unit, UnitType
from interfaces.api.service import APIService
from interfaces.api.schemas import (
    UnitResponse,
    UnitPostBody,
    UnitPatchBody,
)
from interfaces.api.schemas.sta.unit import (
    UnitFields,
    UnitSortByFields,
    UNIT_INCLUDE_RELATIONS,
)

User = get_user_model()


class UnitAPIService(APIService):
    INCLUDE_RELATIONS = UNIT_INCLUDE_RELATIONS

    def get_unit_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = Unit.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)

        queryset = principal.annotate_permissions(queryset)

        try:
            unit = queryset.get()
        except Unit.DoesNotExist:
            raise NotFoundError("Unit does not exist")

        if not principal.can_view(unit):
            raise NotFoundError("Unit does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(unit):
            raise PermissionDeniedError(f"You do not have permission to {action} this unit")

        return unit

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: int | None = None,
        limit: int | None = None,
        sortby: list[str] | None = None,
        filtering: dict | None = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        queryset = Unit.objects

        for field in [
            "workspace_id",
            "datastreams__monitoring_site_id",
            "datastreams__id",
            "type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(UnitSortByFields)),
            rank=has_search,
        )

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        units = list(queryset.all())

        return {
            "data": [UnitResponse.model_validate(unit) for unit in units],
            "meta": meta,
            "included": self.resolve_includes(
                units, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths = [
            self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        unit = self.get_unit_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": UnitResponse.model_validate(unit),
            "included": self.resolve_includes(
                [unit], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: UnitPostBody,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not principal.can_create("Unit", workspace=workspace):
            raise PermissionDeniedError("You do not have permission to create this unit")

        unit = Unit(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(UnitFields.model_fields.keys())),
        )
        unit.full_clean()

        try:
            unit.save()
        except IntegrityError:
            raise ConflictError("The operation could not be completed due to a resource conflict.")

        return {"id": unit.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: UnitPatchBody,
    ):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="edit")
        unit_data = data.dict(
            include=set(UnitFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in unit_data.items():
            setattr(unit, field, value)

        unit.full_clean()
        unit.save()

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="delete")

        try:
            unit.delete()
        except ProtectedError:
            raise ConflictError("Unit in use by one or more datastreams")

        return "Unit deleted"

    def list_unit_types(
        self,
        offset: int | None = None,
        limit: int | None = None,
        sort_desc: bool = False,
    ):
        queryset = UnitType.objects.order_by(f"{'-' if sort_desc else ''}name")
        queryset, meta = self.apply_pagination(queryset, offset, limit)

        return {"data": list(queryset.values_list("name", flat=True)), "meta": meta}
