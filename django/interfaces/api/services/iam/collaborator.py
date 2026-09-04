import uuid
from typing import Optional
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from core.iam.models import Collaborator, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError
from interfaces.api.schemas import CollaboratorPostBody, CollaboratorDeleteBody
from interfaces.api.service import APIService
from .role import RoleAPIService

User = get_user_model()
role_service = RoleAPIService()


class CollaboratorAPIService(APIService):
    @staticmethod
    def serialize_collaborator(collaborator: Collaborator) -> dict:
        return {
            "user": collaborator.user,
            "service_account": collaborator.service_account,
            "role": role_service.serialize_role(collaborator.role, expand_related=False),
        }

    @staticmethod
    def resolve_principal_by_email(email: str):
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            pass

        try:
            return ServiceAccount.objects.get(email=email)
        except ServiceAccount.DoesNotExist:
            pass

        raise BadRequestError(f"No account with email '{email}' found")

    @staticmethod
    def _get_collaborator_by_email(workspace, email: str) -> Collaborator:
        try:
            return Collaborator.objects.select_related(
                "workspace", "user", "service_account"
            ).get(
                Q(user__email=email) | Q(service_account__email=email),
                workspace=workspace,
            )
        except Collaborator.DoesNotExist:
            raise BadRequestError(f"No collaborator with email '{email}' found")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        workspace_id: uuid.UUID,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filtering: Optional[dict] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        queryset = Collaborator.objects.filter(workspace=workspace).select_related(
            "user", "service_account", "role"
        ).prefetch_related("role__permissions")

        for field in [
            "role_id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        # The client fetches collaborators page by page.  Without an explicit
        # ordering, PostgreSQL is free to return tied rows in a different
        # order for each request, which can make a collaborator move between
        # pages or disappear from the merged result.  Keep pagination stable.
        queryset = queryset.order_by("id")

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [self.serialize_collaborator(collaborator) for collaborator in queryset]

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        data: CollaboratorPostBody,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        if not principal.can_create("Collaborator", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to add this collaborator"
            )

        new_collaborator = self.resolve_principal_by_email(data.email)

        collaborator_role = role_service.get_role_for_action(
            principal=principal, uid=data.role_id, action="view", expand_related=True
        )

        collaborator = Collaborator(
            workspace=workspace,
            role=collaborator_role,
            **(
                {"user": new_collaborator}
                if isinstance(new_collaborator, User)
                else {"service_account": new_collaborator}
            ),
        )
        collaborator.full_clean()
        collaborator.save()

        return self.serialize_collaborator(collaborator)

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        data: CollaboratorPostBody,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        collaborator = self._get_collaborator_by_email(workspace, data.email)

        if not principal.can_edit(collaborator):
            raise PermissionDeniedError(
                "You do not have permission to modify this collaborator's role"
            )

        if data.role_id:
            collaborator.role = role_service.get_role_for_action(
                principal=principal,
                uid=data.role_id,
                action="view",
                expand_related=True,
            )

        collaborator.full_clean()
        collaborator.save()

        return self.serialize_collaborator(collaborator)

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        data: CollaboratorDeleteBody,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=workspace_id
        )

        collaborator = self._get_collaborator_by_email(workspace, data.email)

        if not principal.can_delete(collaborator) and getattr(
            principal, "email", None
        ) != getattr(collaborator.user, "email", None):
            raise PermissionDeniedError(
                "You do not have permission to remove this collaborator"
            )

        collaborator.delete()

        return "Collaborator removed from workspace"
