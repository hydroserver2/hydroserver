import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from interfaces.api.schemas import (
    APIKeyPostBody,
    APIKeyPatchBody,
    APIKeySummaryResponse,
    APIKeyDetailResponse,
    APIKeySummaryPostResponse,
    APIKeyDetailPostResponse,
)
from interfaces.api.schemas.api_key import APIKeyOrderByFields
from interfaces.api.service import ServiceUtils
from .role import RoleService

User = get_user_model()
role_service = RoleService()


class APIKeyService(ServiceUtils):
    def get_api_key_for_action(
        self,
        principal: User,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        try:
            api_key = APIKey.objects
            if expand_related:
                api_key = self.select_expanded_fields(api_key)
            api_key = api_key.get(workspace=workspace, pk=uid)
        except APIKey.DoesNotExist:
            raise HttpError(404, "API key does not exist")

        permissions = api_key.get_principal_permissions(principal=principal)

        if "view" not in permissions:
            raise HttpError(404, "API key does not exist")

        if action not in permissions:
            raise HttpError(403, f"You do not have permission to {action} this API key")

        return api_key

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace", "role").prefetch_related(
            "role__permissions"
        )

    def list(
        self,
        principal: Optional[User | APIKey],
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

        queryset = APIKey.objects.filter(workspace=workspace)

        for field in [
            "role_id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(APIKeyOrderByFields))
            )
        else:
            queryset = queryset.order_by("id")

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                APIKeyDetailResponse.model_validate(api_key)
                if expand_related
                else APIKeySummaryResponse.model_validate(api_key)
            )
            for api_key in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        api_key = self.get_api_key_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="view",
            expand_related=expand_related,
        )

        return (
            APIKeyDetailResponse.model_validate(api_key)
            if expand_related
            else APIKeySummaryResponse.model_validate(api_key)
        )

    def create(
        self,
        principal: User,
        workspace_id: uuid.UUID,
        data: APIKeyPostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        if not APIKey.can_principal_create(principal=principal, workspace=workspace):
            raise HttpError(403, "You do not have permission to create this API key")

        apikey_role = role_service.get(principal=principal, uid=data.role_id)

        if not apikey_role.is_apikey_role:
            raise HttpError(400, "Role not supported for API key assignment")

        try:
            api_key, raw_key = APIKey.objects.create_with_key(
                pk=data.id, workspace=workspace, **data.dict()
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        api_key = self.get_api_key_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=api_key.id,
            action="view",
            expand_related=expand_related,
        )

        api_key.key = raw_key

        return (
            APIKeyDetailPostResponse.model_validate(api_key)
            if expand_related
            else APIKeySummaryPostResponse.model_validate(api_key)
        )

    def update(
        self,
        principal: User,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        data: APIKeyPatchBody,
        expand_related: Optional[bool] = None,
    ):
        api_key = self.get_api_key_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
        )
        api_key_body = data.dict(exclude_unset=True)

        if "role_id" in api_key_body:
            apikey_role = role_service.get(principal=principal, uid=data.role_id)

            if not apikey_role.is_apikey_role:
                raise HttpError(400, "Role not supported for API key assignment")

        for field, value in api_key_body.items():
            setattr(api_key, field, value)

        api_key.save()

        return self.get(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            expand_related=expand_related,
        )

    def delete(self, principal: User, workspace_id: uuid.UUID, uid: uuid.UUID):
        api_key = self.get_api_key_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="delete",
            expand_related=True,
        )

        api_key.delete()

        return "API key deleted"

    def regenerate(
        self,
        principal: User,
        workspace_id: uuid.UUID,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        api_key = self.get_api_key_for_action(
            principal=principal,
            workspace_id=workspace_id,
            uid=uid,
            action="edit",
            expand_related=expand_related,
        )

        raw_key = api_key.generate_key()
        api_key.key = raw_key

        return (
            APIKeyDetailPostResponse.model_validate(api_key)
            if expand_related
            else APIKeySummaryPostResponse.model_validate(api_key)
        )
