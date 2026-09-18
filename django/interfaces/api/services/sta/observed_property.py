import uuid

from typing import Optional, Literal, get_args
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ObservedProperty, VariableType
from interfaces.api.service import APIService
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.schemas import (
    ObservedPropertyResponse,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from interfaces.api.schemas.sta.observed_property import (
    ObservedPropertyFields,
    ObservedPropertySortByFields,
    OBSERVED_PROPERTY_INCLUDE_RELATIONS,
)

User = get_user_model()


class ObservedPropertyAPIService(APIService):
    INCLUDE_RELATIONS = OBSERVED_PROPERTY_INCLUDE_RELATIONS

    def get_observed_property_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = ObservedProperty.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)
        queryset = principal.annotate_permissions(queryset)

        try:
            observed_property = queryset.get()
        except ObservedProperty.DoesNotExist:
            raise NotFoundError("Observed property does not exist")

        if not principal.can_view(observed_property):
            raise NotFoundError("Observed property does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(observed_property):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this observed property"
            )

        return observed_property

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        queryset = ObservedProperty.objects
        requested_includes = self.resolve_include_set(include)

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
            list(get_args(ObservedPropertySortByFields)),
            rank=has_search,
        )

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        observed_properties = list(queryset.all())

        return {
            "data": [
                ObservedPropertyResponse.model_validate(observed_property)
                for observed_property in observed_properties
            ],
            "meta": meta,
            "included": self.resolve_includes(
                observed_properties, requested_includes, self.INCLUDE_RELATIONS
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
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": ObservedPropertyResponse.model_validate(observed_property),
            "included": self.resolve_includes(
                [observed_property], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservedPropertyPostBody,
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
            raise PermissionDeniedError(
                "You do not have permission to create this observed property"
            )

        observed_property = ObservedProperty(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ObservedPropertyFields.model_fields.keys())),
        )
        observed_property.full_clean()

        try:
            observed_property.save()
        except IntegrityError:
            raise ConflictError("The operation could not be completed due to a resource conflict.")

        return {"id": observed_property.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ObservedPropertyPatchBody,
    ):
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="edit"
        )
        observed_property_data = data.dict(
            include=set(ObservedPropertyFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in observed_property_data.items():
            setattr(observed_property, field, value)

        observed_property.full_clean()
        observed_property.save()

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        observed_property = self.get_observed_property_for_action(
            principal=principal, uid=uid, action="delete"
        )

        try:
            observed_property.delete()
        except ProtectedError:
            raise ConflictError("Observed property in use by one or more datastreams")

        return "Observed property deleted"

    def list_variable_types(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sort_desc: bool = False,
    ):
        queryset = VariableType.objects.order_by(f"{'-' if sort_desc else ''}name")
        queryset, meta = self.apply_pagination(queryset, offset, limit)

        return {"data": list(queryset.values_list("name", flat=True)), "meta": meta}
