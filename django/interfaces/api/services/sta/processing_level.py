import uuid

from typing import Optional, Literal, get_args
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ProcessingLevel
from interfaces.api.service import APIService
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.schemas import (
    ProcessingLevelResponse,
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
)
from interfaces.api.schemas.sta.processing_level import (
    ProcessingLevelFields,
    ProcessingLevelOrderByFields,
    PROCESSING_LEVEL_INCLUDE_RELATIONS,
)

User = get_user_model()


class ProcessingLevelAPIService(APIService):
    INCLUDE_RELATIONS = PROCESSING_LEVEL_INCLUDE_RELATIONS

    def get_processing_level_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = ProcessingLevel.objects.filter(pk=uid)

        if select_related:
            queryset = queryset.select_related(*select_related)

        queryset = principal.annotate_permissions(queryset)

        try:
            processing_level = queryset.get()
        except ProcessingLevel.DoesNotExist:
            raise NotFoundError("Processing level does not exist")

        if not principal.can_view(processing_level):
            raise NotFoundError("Processing level does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            processing_level
        ):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this processing level"
            )

        return processing_level

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
        queryset = ProcessingLevel.objects

        for field in [
            "workspace_id",
            "datastreams__monitoring_site_id",
            "datastreams__id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(ProcessingLevelOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        processing_levels = list(queryset.all())

        return {
            "data": [
                ProcessingLevelResponse.model_validate(processing_level)
                for processing_level in processing_levels
            ],
            "meta": meta,
            "included": self.resolve_includes(
                processing_levels, requested_includes, self.INCLUDE_RELATIONS
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
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": ProcessingLevelResponse.model_validate(processing_level),
            "included": self.resolve_includes(
                [processing_level], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ProcessingLevelPostBody,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not principal.can_create("ProcessingLevel", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to create this processing level"
            )

        processing_level = ProcessingLevel(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ProcessingLevelFields.model_fields.keys())),
        )
        processing_level.full_clean()

        try:
            processing_level.save()
        except IntegrityError:
            raise ConflictError("The operation could not be completed due to a resource conflict.")

        return {"id": processing_level.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ProcessingLevelPatchBody,
    ):
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="edit"
        )
        processing_level_data = data.dict(
            include=set(ProcessingLevelFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in processing_level_data.items():
            setattr(processing_level, field, value)

        processing_level.full_clean()
        processing_level.save()

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="delete"
        )

        try:
            processing_level.delete()
        except ProtectedError:
            raise ConflictError("Processing level in use by one or more datastreams")

        return "Processing level deleted"
