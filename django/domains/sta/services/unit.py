import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from domains.sta.models import Unit, UnitType
from interfaces.api.schemas import (
    UnitSummaryResponse,
    UnitDetailResponse,
    UnitPostBody,
    UnitPatchBody,
)
from interfaces.api.schemas.unit import UnitFields, UnitOrderByFields
from interfaces.api.service import ServiceUtils

User = get_user_model()


class UnitService(ServiceUtils):
    def get_unit_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        try:
            unit = Unit.objects
            if expand_related:
                unit = self.select_expanded_fields(unit)
            unit = unit.get(pk=uid)
        except Unit.DoesNotExist:
            raise HttpError(404, "Unit does not exist")

        unit_permissions = unit.get_principal_permissions(principal=principal)

        if "view" not in unit_permissions:
            raise HttpError(404, "Unit does not exist")

        if action not in unit_permissions:
            raise HttpError(403, f"You do not have permission to {action} this unit")

        return unit

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

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
        queryset = Unit.objects

        for field in [
            "workspace_id",
            "datastreams__thing_id",
            "datastreams__id",
            "unit_type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(UnitOrderByFields)),
                {"type": "unit_type"},
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = queryset.visible(principal=principal).distinct()

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
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
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
        principal: User | APIKey,
        data: UnitPostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not Unit.can_principal_create(principal=principal, workspace=workspace):
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
        principal: User | APIKey,
        uid: uuid.UUID,
        data: UnitPatchBody,
        expand_related: Optional[bool] = None,
    ):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="edit")
        unit_data = data.dict(
            include=set(UnitFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in unit_data.items():
            setattr(unit, field, value)

        unit.save()

        return self.get(principal=principal, uid=unit.id, expand_related=expand_related)

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        unit = self.get_unit_for_action(principal=principal, uid=uid, action="delete")

        if unit.datastreams.exists():
            raise HttpError(409, "Unit in use by one or more datastreams")

        unit.delete()

        return "Unit deleted"

    def list_unit_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = UnitType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
