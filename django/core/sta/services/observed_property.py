import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ObservedProperty, VariableType
from interfaces.api.schemas import (
    ObservedPropertySummaryResponse,
    ObservedPropertyDetailResponse,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from interfaces.api.schemas.sta.observed_property import (
    ObservedPropertyFields,
    ObservedPropertyOrderByFields,
)
from core.service import ServiceUtils

User = get_user_model()


class ObservedPropertyService(ServiceUtils):
    def get_observed_property_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = ObservedProperty.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        queryset = principal.annotate_permissions(queryset)

        try:
            observed_property = queryset.get()
        except ObservedProperty.DoesNotExist:
            raise HttpError(404, "Observed property does not exist")

        if not principal.can_view(observed_property):
            raise HttpError(404, "Observed property does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(observed_property):
            raise HttpError(
                403, f"You do not have permission to {action} this observed property"
            )

        return observed_property

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

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
        queryset = ObservedProperty.objects

        for field in [
            "workspace_id",
            "datastreams__monitoring_site_id",
            "datastreams__id",
            "observed_property_type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(ObservedPropertyOrderByFields)),
                {"type": "observed_property_type"},
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                ObservedPropertyDetailResponse.model_validate(observed_property)
                if expand_related
                else ObservedPropertySummaryResponse.model_validate(observed_property)
            )
            for observed_property in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            ObservedPropertyDetailResponse.model_validate(observed_property)
            if expand_related
            else ObservedPropertySummaryResponse.model_validate(observed_property)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservedPropertyPostBody,
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

        if not principal.can_create("ObservedProperty", workspace=workspace):
            raise HttpError(
                403, "You do not have permission to create this observed property"
            )

        try:
            observed_property = ObservedProperty.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(ObservedPropertyFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal, uid=observed_property.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ObservedPropertyPatchBody,
        expand_related: Optional[bool] = None,
    ):
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="edit", expand_related=expand_related
        )
        observed_property_data = data.dict(
            include=set(ObservedPropertyFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in observed_property_data.items():
            setattr(observed_property, field, value)

        observed_property.save()

        return self.get(
            principal=principal, uid=observed_property.id, expand_related=expand_related
        )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="delete"
        )

        if observed_property.datastreams.exists():
            raise HttpError(409, "Observed property in use by one or more datastreams")

        observed_property.delete()

        return "Observed property deleted"

    def list_variable_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = VariableType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
