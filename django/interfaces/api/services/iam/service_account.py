import uuid

from typing import Optional, Literal, get_args
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from core.iam.models import Collaborator, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.schemas import (
    ServiceAccountResponse,
    ServiceAccountPostBody,
    ServiceAccountPatchBody,
)
from interfaces.api.schemas.iam.service_account import (
    ServiceAccountInputFields,
    ServiceAccountOrderByFields,
    SERVICE_ACCOUNT_INCLUDE_RELATIONS,
)

from .role import RoleAPIService

User = get_user_model()
role_service = RoleAPIService()


class ServiceAccountAPIService(APIService):
    INCLUDE_RELATIONS = SERVICE_ACCOUNT_INCLUDE_RELATIONS

    def get_service_account_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        queryset = ServiceAccount.objects.filter(workspace=workspace, pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)

        queryset = principal.annotate_permissions(queryset)

        try:
            service_account = queryset.get()
        except ServiceAccount.DoesNotExist:
            raise NotFoundError("Service account does not exist")

        if not principal.can_view(service_account):
            raise NotFoundError("Service account does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            service_account
        ):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this service account"
            )

        return service_account

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
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

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        service_accounts = list(queryset.all())

        return {
            "data": [
                ServiceAccountResponse.model_validate(service_account)
                for service_account in service_accounts
            ],
            "meta": meta,
            "included": self.resolve_includes(
                service_accounts, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths = [
            self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="view",
            select_related=select_paths,
        )

        return {
            "data": ServiceAccountResponse.model_validate(service_account),
            "included": self.resolve_includes(
                [service_account], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        data: ServiceAccountPostBody,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        if not principal.can_create("ServiceAccount", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to create this service account"
            )

        collaborator_role = None
        if data.role_id is not None:
            if not principal.can_create("Collaborator", workspace=workspace):
                raise PermissionDeniedError(
                    "You do not have permission to add this collaborator"
                )

            collaborator_role = role_service.get_role_for_action(
                principal=principal,
                uid=data.role_id,
                action="view",
            )

        service_account = ServiceAccount(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ServiceAccountInputFields.model_fields.keys())),
        )
        raw_key = service_account.generate_key()
        service_account.full_clean(exclude=["email"])

        try:
            service_account.save()
        except IntegrityError:
            raise ConflictError(
                "The operation could not be completed due to a resource conflict."
            )

        if collaborator_role is not None:
            collaborator = Collaborator(
                workspace=workspace,
                service_account=service_account,
                role=collaborator_role,
            )
            collaborator.full_clean()
            collaborator.save()

        return {"id": service_account.pk, "key": raw_key}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        data: ServiceAccountPatchBody,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
        )
        service_account_body = data.dict(
            include=set(ServiceAccountInputFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in service_account_body.items():
            setattr(service_account, field, value)

        service_account.full_clean()
        service_account.save()

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
        )

        service_account.delete()

        return "Service account deleted"

    def regenerate(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
    ):
        service_account = self.get_service_account_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
        )

        raw_key = service_account.generate_key()

        return {"key": raw_key}
