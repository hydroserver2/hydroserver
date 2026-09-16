import uuid
from typing import Literal, Optional, get_args

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.schemas.etl.mapping import (
    EtlMappingFields,
    EtlMappingOrderByFields,
    EtlMappingPatchBody,
    EtlMappingPostBody,
    EtlMappingResponse,
    ETL_MAPPING_INCLUDE_RELATIONS,
)
from interfaces.api.services.etl.task import EtlTaskAPIService
from interfaces.api.services.sta.datastream import DatastreamAPIService
from processing.etl.models import EtlMapping

User = get_user_model()
datastream_service = DatastreamAPIService()
etl_task_service = EtlTaskAPIService()


class EtlMappingAPIService(APIService):
    INCLUDE_RELATIONS = ETL_MAPPING_INCLUDE_RELATIONS

    @classmethod
    def _include_query_hints(cls, requested_includes: set[str]) -> tuple[list[str], list[str]]:
        select_paths = [
            cls.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        prefetch_paths = []
        if "targetDatastream" in requested_includes:
            select_paths.append("target_datastream__monitoring_site")
            prefetch_paths.append("target_datastream__datastream_linked_resources")
        return select_paths, prefetch_paths

    def get_mapping_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ) -> EtlMapping:
        queryset = EtlMapping.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        try:
            mapping = queryset.get()
        except EtlMapping.DoesNotExist:
            raise NotFoundError(f"EtlMapping with ID {uid} does not exist.")

        if not principal.can_view(mapping):
            raise NotFoundError(f"EtlMapping with ID {uid} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(mapping):
            raise PermissionDeniedError(f"You do not have permission to {action} this mapping.")

        return mapping

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        filtering = filtering or {}

        queryset = EtlMapping.objects.all()

        for field in ["source_identifier", "target_datastream_id", "etl_task_id"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if "workspace_id" in filtering:
            queryset = self.apply_filters(
                queryset, "etl_task__data_connection__workspace_id", filtering["workspace_id"]
            )

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(EtlMappingOrderByFields))
            )
        else:
            queryset = queryset.order_by("id")

        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)

        mappings = list(queryset.all())

        return {
            "data": [EtlMappingResponse.model_validate(m) for m in mappings],
            "meta": meta,
            "included": self.resolve_includes(
                mappings, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths, prefetch_paths = self._include_query_hints(requested_includes)

        mapping = self.get_mapping_for_action(
            principal=principal,
            uid=uid,
            action="view",
            select_related=select_paths,
            prefetch_related=prefetch_paths,
        )

        return {
            "data": EtlMappingResponse.model_validate(mapping),
            "included": self.resolve_includes(
                [mapping], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: EtlMappingPostBody,
    ):
        if data.id is not None and data.id.version != 7:
            raise BadRequestError(f"Invalid UUID version {data.id.version}. Expected 7.")

        task = etl_task_service.get_task_for_action(principal, data.etl_task_id, action="view")

        if not principal.can_create("EtlMapping", workspace=task.workspace):
            raise PermissionDeniedError(
                "You do not have permission to create mappings on this task."
            )

        datastream_service.get_datastream_for_action(
            principal=principal, uid=data.target_datastream_id, action="edit"
        )

        mapping = EtlMapping(
            pk=data.id,
            etl_task=task,
            **data.dict(include=set(EtlMappingFields.model_fields.keys())),
        )
        mapping.full_clean()

        try:
            mapping.save()
        except IntegrityError:
            raise ConflictError("The operation could not be completed due to a resource conflict.")

        return {"id": mapping.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: EtlMappingPatchBody,
    ):
        mapping = self.get_mapping_for_action(principal=principal, uid=uid, action="edit")

        if data.target_datastream_id is not Unset:
            datastream_service.get_datastream_for_action(
                principal=principal, uid=data.target_datastream_id, action="edit"
            )

        update_fields = data.dict(
            include=set(EtlMappingFields.model_fields.keys()), exclude_unset=True
        )
        for field, value in update_fields.items():
            setattr(mapping, field, value)

        mapping.full_clean()
        mapping.save()

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        mapping = self.get_mapping_for_action(principal=principal, uid=uid, action="delete")
        mapping.delete()
