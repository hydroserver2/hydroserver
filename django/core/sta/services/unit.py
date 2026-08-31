import uuid

from typing import Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Unit, UnitType
from core.service import ServiceUtils
from interfaces.api.schemas import (
    UnitSummaryResponse,
    UnitDetailResponse,
    UnitPostBody,
    UnitPatchBody,
)
from interfaces.api.schemas.sta.unit import UnitFields, UnitOrderByFields

User = get_user_model()


class UnitService(ServiceUtils):
    def get_unit_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: bool | None = None,
    ):
        queryset = Unit.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        queryset = principal.annotate_permissions(queryset)

        try:
            unit = queryset.get()
        except Unit.DoesNotExist:
            raise HttpError(404, "Unit does not exist")

        if not principal.can_view(unit):
            raise HttpError(404, "Unit does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(unit):
            raise HttpError(403, f"You do not have permission to {action} this unit")

        return unit

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        page: int | None = None,
        page_size: int | None = None,
        order_by: list[str] | None = None,
        filtering: dict | None = None,
        expand_related: bool | None = None,
    ):
        queryset = Unit.objects

        for field in [
            "workspace_id",
            "datastreams__monitoring_site_id",
            "datastreams__id",
            "type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(UnitOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                UnitDetailResponse.model_validate(unit)
                if expand_related
                else UnitSummaryResponse.model_validate(unit)
            )
            for unit in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: bool | None = None,
    ):
        unit = self.get_unit_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            UnitDetailResponse.model_validate(unit)
            if expand_related
            else UnitSummaryResponse.model_validate(unit)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: UnitPostBody,
        expand_related: bool | None = None,
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
            raise HttpError(403, "You do not have permission to create this unit")

        try:
            unit = Unit.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(UnitFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(principal=principal, uid=unit.pk, expand_related=expand_related)

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: UnitPatchBody,
        expand_related: bool | None = None,
    ):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="edit")
        unit_data = data.dict(
            include=set(UnitFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in unit_data.items():
            setattr(unit, field, value)

        unit.save()

        return self.get(principal=principal, uid=unit.id, expand_related=expand_related)

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="delete")

        if unit.datastreams.exists():
            raise HttpError(409, "Unit in use by one or more datastreams")

        unit.delete()

        return "Unit deleted"

    def list_unit_types(
        self,
        response: HttpResponse,
        page: int | None = None,
        page_size: int | None = None,
        order_desc: bool = False,
    ):
        queryset = UnitType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
