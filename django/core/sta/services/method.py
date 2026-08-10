import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Method, MethodType
from interfaces.api.schemas import (
    MethodSummaryResponse,
    MethodDetailResponse,
    MethodPostBody,
    MethodPatchBody,
)
from interfaces.api.schemas.sta.method import MethodFields, MethodOrderByFields
from core.service import ServiceUtils

User = get_user_model()


class MethodService(ServiceUtils):
    def get_method_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = Method.objects.filter(pk=uid)

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.annotate_permissions(queryset)

        try:
            method = queryset.get()
        except Method.DoesNotExist:
            raise HttpError(404, "Method does not exist")

        if not principal.can_view(method):
            raise HttpError(404, "Method does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(method):
            raise HttpError(403, f"You do not have permission to {action} this method")

        return method

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
        queryset = Method.objects

        for field in [
            "workspace_id",
            "datastreams__monitoring_site_id",
            "datastreams__id",
            "type",
            "sensor_model",
            "sensor_model_manufacturer",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(MethodOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                MethodDetailResponse.model_validate(method)
                if expand_related
                else MethodSummaryResponse.model_validate(method)
            )
            for method in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        method = self.get_method_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            MethodDetailResponse.model_validate(method)
            if expand_related
            else MethodSummaryResponse.model_validate(method)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: MethodPostBody,
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

        if not principal.can_create("Method", workspace=workspace):
            raise HttpError(403, "You do not have permission to create this method")

        try:
            method = Method.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(MethodFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(
                409,
                "The operation could not be completed due to a resource conflict.",
            )

        return self.get(
            principal=principal, uid=method.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: MethodPatchBody,
        expand_related: Optional[bool] = None,
    ):
        method = self.get_method_for_action(principal=principal, uid=uid, action="edit")
        method_data = data.dict(
            include=set(MethodFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in method_data.items():
            setattr(method, field, value)

        method.save()

        return self.get(
            principal=principal, uid=method.id, expand_related=expand_related
        )

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        method = self.get_method_for_action(
            principal=principal, uid=uid, action="delete"
        )

        if method.datastreams.exists():
            raise HttpError(409, "Method in use by one or more datastreams")

        method.delete()

        return "Method deleted"

    def list_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = MethodType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
