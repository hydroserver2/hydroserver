import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ProcessingLevel
from interfaces.api.schemas import (
    ProcessingLevelSummaryResponse,
    ProcessingLevelDetailResponse,
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
)
from interfaces.api.schemas.sta.processing_level import (
    ProcessingLevelFields,
    ProcessingLevelOrderByFields,
)
from core.service import ServiceUtils

User = get_user_model()


class ProcessingLevelService(ServiceUtils):
    def get_processing_level_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = ProcessingLevel.objects.filter(pk=uid)

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.annotate_permissions(queryset)

        try:
            processing_level = queryset.get()
        except ProcessingLevel.DoesNotExist:
            raise HttpError(404, "Processing level does not exist")

        if not principal.can_view(processing_level):
            raise HttpError(404, "Processing level does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            processing_level
        ):
            raise HttpError(
                403, f"You do not have permission to {action} this processing level"
            )

        return processing_level

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
        queryset = ProcessingLevel.objects

        for field in [
            "workspace_id",
            "datastreams__thing_id",
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

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                ProcessingLevelDetailResponse.model_validate(processing_level)
                if expand_related
                else ProcessingLevelSummaryResponse.model_validate(processing_level)
            )
            for processing_level in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            ProcessingLevelDetailResponse.model_validate(processing_level)
            if expand_related
            else ProcessingLevelSummaryResponse.model_validate(processing_level)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ProcessingLevelPostBody,
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

        if not principal.can_create("ProcessingLevel", workspace=workspace):
            raise HttpError(
                403, "You do not have permission to create this processing level"
            )

        try:
            processing_level = ProcessingLevel.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(ProcessingLevelFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal, uid=processing_level.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ProcessingLevelPatchBody,
        expand_related: Optional[bool] = None,
    ):
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="edit"
        )
        processing_level_data = data.dict(
            include=set(ProcessingLevelFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in processing_level_data.items():
            setattr(processing_level, field, value)

        processing_level.save()

        return self.get(
            principal=principal, uid=processing_level.id, expand_related=expand_related
        )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        processing_level = self.get_processing_level_for_action(
            principal=principal, uid=uid, action="delete"
        )

        if processing_level.datastreams.exists():
            raise HttpError(409, "Processing level in use by one or more datastreams")

        processing_level.delete()

        return "Processing level deleted"
