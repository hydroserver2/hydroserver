import uuid

from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.service import ServiceUtils
from interfaces.api.schemas import (
    ServiceAccountSummaryResponse,
    ServiceAccountDetailResponse,
    ServiceAccountPostBody,
    ServiceAccountPatchBody,
    ServiceAccountSummaryPostResponse,
    ServiceAccountDetailPostResponse,
)
from interfaces.api.schemas.iam.service_account import (
    ServiceAccountFields,
    ServiceAccountOrderByFields,
)

User = get_user_model()


class ServiceAccountService(ServiceUtils):
    def get_service_account_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        queryset = ServiceAccount.objects.filter(workspace=workspace, pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        queryset = principal.annotate_permissions(queryset)

        try:
            service_account = queryset.get()
        except ServiceAccount.DoesNotExist:
            raise HttpError(404, "Service account does not exist")

        if not principal.can_view(service_account):
            raise HttpError(404, "Service account does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            service_account
        ):
            raise HttpError(
                403, f"You do not have permission to {action} this service account"
            )

        return service_account

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        workspace_id: uuid.UUID,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        queryset = ServiceAccount.objects.filter(workspace=workspace)

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(ServiceAccountOrderByFields))
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                ServiceAccountDetailResponse.model_validate(service_account)
                if expand_related
                else ServiceAccountSummaryResponse.model_validate(service_account)
            )
            for service_account in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="view",
            expand_related=expand_related,
        )

        return (
            ServiceAccountDetailResponse.model_validate(service_account)
            if expand_related
            else ServiceAccountSummaryResponse.model_validate(service_account)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        data: ServiceAccountPostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        if not principal.can_create("ServiceAccount", workspace=workspace):
            raise HttpError(
                403, "You do not have permission to create this service account"
            )

        service_account = ServiceAccount(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ServiceAccountFields.model_fields.keys())),
        )
        raw_key = service_account.generate_key()

        try:
            service_account.save()
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=service_account.id,
            action="view",
            expand_related=expand_related,
        )

        service_account.key = raw_key

        return (
            ServiceAccountDetailPostResponse.model_validate(service_account)
            if expand_related
            else ServiceAccountSummaryPostResponse.model_validate(service_account)
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        data: ServiceAccountPatchBody,
        expand_related: Optional[bool] = None,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
        )
        service_account_body = data.dict(
            include=set(ServiceAccountFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in service_account_body.items():
            setattr(service_account, field, value)

        service_account.save()

        return self.get(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            expand_related=expand_related,
        )

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="delete",
            expand_related=True,
        )

        service_account.delete()

        return "Service account deleted"

    def regenerate(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
            expand_related=expand_related,
        )

        raw_key = service_account.generate_key()
        service_account.key = raw_key

        return (
            ServiceAccountDetailPostResponse.model_validate(service_account)
            if expand_related
            else ServiceAccountSummaryPostResponse.model_validate(service_account)
        )
