import uuid

from typing import Optional, Literal, get_args
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Method, MethodType
from interfaces.api.service import APIService
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.schemas import (
    MethodResponse,
    MethodPostBody,
    MethodPatchBody,
)
from interfaces.api.schemas.sta.method import (
    MethodFields,
    MethodSortByFields,
    METHOD_INCLUDE_RELATIONS,
)

User = get_user_model()


class MethodAPIService(APIService):
    INCLUDE_RELATIONS = METHOD_INCLUDE_RELATIONS

    def get_method_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = Method.objects.filter(pk=uid)

        if select_related:
            queryset = queryset.select_related(*select_related)

        queryset = principal.annotate_permissions(queryset)

        try:
            method = queryset.get()
        except Method.DoesNotExist:
            raise NotFoundError("Method does not exist")

        if not principal.can_view(method):
            raise NotFoundError("Method does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(method):
            raise PermissionDeniedError(f"You do not have permission to {action} this method")

        return method

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
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

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(MethodSortByFields)),
            rank=has_search,
        )

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        methods = list(queryset.all())

        return {
            "data": [MethodResponse.model_validate(method) for method in methods],
            "meta": meta,
            "included": self.resolve_includes(
                methods, requested_includes, self.INCLUDE_RELATIONS
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
        method = self.get_method_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": MethodResponse.model_validate(method),
            "included": self.resolve_includes(
                [method], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: MethodPostBody,
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
            raise PermissionDeniedError("You do not have permission to create this method")

        method = Method(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(MethodFields.model_fields.keys())),
        )
        method.full_clean()

        try:
            method.save()
        except IntegrityError:
            raise ConflictError(
                "The operation could not be completed due to a resource conflict."
            )

        return {"id": method.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: MethodPatchBody,
    ):
        method = self.get_method_for_action(principal=principal, uid=uid, action="edit")
        method_data = data.dict(
            include=set(MethodFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in method_data.items():
            setattr(method, field, value)

        method.full_clean()
        method.save()

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        method = self.get_method_for_action(
            principal=principal, uid=uid, action="delete"
        )

        try:
            method.delete()
        except ProtectedError:
            raise ConflictError("Method in use by one or more datastreams")

        return "Method deleted"

    def list_types(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sort_desc: bool = False,
    ):
        queryset = MethodType.objects.order_by(f"{'-' if sort_desc else ''}name")
        queryset, meta = self.apply_pagination(queryset, offset, limit)

        return {"data": list(queryset.values_list("name", flat=True)), "meta": meta}
