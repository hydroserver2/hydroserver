import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from domains.sta.models import ObservedProperty, VariableType
from interfaces.api.schemas import (
    ObservedPropertySummaryResponse,
    ObservedPropertyDetailResponse,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from interfaces.api.schemas.observed_property import (
    ObservedPropertyFields,
    ObservedPropertyOrderByFields,
)
from interfaces.api.service import ServiceUtils

User = get_user_model()


class ObservedPropertyService(ServiceUtils):
    def get_observed_property_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        try:
            observed_property = ObservedProperty.objects
            if expand_related:
                observed_property = self.select_expanded_fields(observed_property)
            observed_property = observed_property.get(pk=uid)
        except ObservedProperty.DoesNotExist:
            raise HttpError(404, "Observed property does not exist")

        observed_property_permissions = observed_property.get_principal_permissions(
            principal=principal
        )

        if "view" not in observed_property_permissions:
            raise HttpError(404, "Observed property does not exist")

        if action not in observed_property_permissions:
            raise HttpError(
                403, f"You do not have permission to {action} this observed property"
            )

        return observed_property

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
        queryset = ObservedProperty.objects

        for field in [
            "workspace_id",
            "datastreams__thing_id",
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

        queryset = queryset.visible(principal=principal).distinct()

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
        principal: Optional[User | APIKey],
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
        principal: User | APIKey,
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

        if not ObservedProperty.can_principal_create(
            principal=principal, workspace=workspace
        ):
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
        principal: User | APIKey,
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

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
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
