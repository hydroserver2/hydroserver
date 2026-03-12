import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from domains.etl.models import OrchestrationSystem
from interfaces.api.schemas import (
    OrchestrationSystemSummaryResponse,
    OrchestrationSystemDetailResponse,
    OrchestrationSystemPostBody,
    OrchestrationSystemPatchBody,
)
from interfaces.api.schemas.orchestration_system import (
    OrchestrationSystemFields,
    OrchestrationSystemOrderByFields,
)
from interfaces.api.service import ServiceUtils

User = get_user_model()


class OrchestrationSystemService(ServiceUtils):

    def get_orchestration_system_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
        raise_400: bool = False,
    ):
        try:
            orchestration_system = OrchestrationSystem.objects
            if expand_related:
                orchestration_system = self.select_expanded_fields(orchestration_system)
            orchestration_system = orchestration_system.get(pk=uid)
        except OrchestrationSystem.DoesNotExist:
            raise HttpError(
                404 if not raise_400 else 400, "Orchestration system does not exist"
            )

        orchestration_system_permissions = (
            orchestration_system.get_principal_permissions(principal=principal)
        )

        if "view" not in orchestration_system_permissions:
            raise HttpError(
                404 if not raise_400 else 400, "Orchestration system does not exist"
            )

        if action not in orchestration_system_permissions:
            raise HttpError(
                403 if not raise_400 else 400,
                f"You do not have permission to {action} this orchestration system",
            )

        return orchestration_system

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
        queryset = OrchestrationSystem.objects

        for field in [
            "workspace_id",
            "orchestration_system_type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(OrchestrationSystemOrderByFields)),
                {"type": "orchestration_system_type"},
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                OrchestrationSystemDetailResponse.model_validate(orchestration_system)
                if expand_related
                else OrchestrationSystemSummaryResponse.model_validate(
                    orchestration_system
                )
            )
            for orchestration_system in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        orchestration_system = self.get_orchestration_system_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            OrchestrationSystemDetailResponse.model_validate(orchestration_system)
            if expand_related
            else OrchestrationSystemSummaryResponse.model_validate(orchestration_system)
        )

    def create(
        self,
        principal: User | APIKey,
        data: OrchestrationSystemPostBody,
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

        if not OrchestrationSystem.can_principal_create(
            principal=principal, workspace=workspace
        ) or data.orchestration_system_type.upper() == "INTERNAL":
            raise HttpError(
                403, "You do not have permission to create this orchestration system"
            )

        try:
            orchestration_system = OrchestrationSystem.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(OrchestrationSystemFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal,
            uid=orchestration_system.id,
            expand_related=expand_related,
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        data: OrchestrationSystemPatchBody,
        expand_related: Optional[bool] = None,
    ):
        orchestration_system = self.get_orchestration_system_for_action(
            principal=principal, uid=uid, action="edit", expand_related=expand_related
        )
        orchestration_system_data = data.dict(
            include=set(OrchestrationSystemFields.model_fields.keys()),
            exclude_unset=True,
        )

        for field, value in orchestration_system_data.items():
            if field == "orchestration_system_type" and value.upper() == "INTERNAL":
                raise HttpError(
                    403, "You do not have permission to set this orchestration system type to INTERNAL"
                )
            setattr(orchestration_system, field, value)

        orchestration_system.save()

        return self.get(
            principal=principal,
            uid=orchestration_system.id,
            expand_related=expand_related,
        )

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        orchestration_system = self.get_orchestration_system_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )

        orchestration_system.delete()

        return "Orchestration system deleted"
