import uuid
from typing import Optional
from ninja.errors import HttpError
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from core.iam.models import Collaborator, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.schemas import CollaboratorPostBody, CollaboratorDeleteBody
from core.service import ServiceUtils
from .role import RoleService

User = get_user_model()
role_service = RoleService()


class CollaboratorService(ServiceUtils):
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

        raise HttpError(400, f"No account with email '{email}' found")

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
            raise HttpError(403, "You do not have permission to add this collaborator")

        new_collaborator = self.resolve_principal_by_email(data.email)

        workspace_collaborator_emails = {
            email for email_pair in Collaborator.objects.filter(workspace=workspace).values_list(
                "user__email", "service_account__email"
            ) for email in email_pair if email
        }

        if new_collaborator.email in workspace_collaborator_emails:
            raise HttpError(
                400,
                f"Account with email '{data.email}' already collaborates on the workspace",
            )

        if isinstance(new_collaborator, User) and new_collaborator.email == workspace.owner.email:
            raise HttpError(
                400, f"Account with email '{data.email}' already owns the workspace"
            )

        collaborator_role = role_service.get_role_for_action(
            principal=principal, uid=data.role_id, action="view", expand_related=True
        )

        if collaborator_role.workspace and collaborator_role.workspace != workspace:
            raise HttpError(400, "Role does not belong to the workspace")

        if isinstance(new_collaborator, User):
            collaborator = Collaborator.objects.create(
                workspace=workspace, user=new_collaborator, role_id=collaborator_role.id
            )
        else:
            collaborator = Collaborator.objects.create(
                workspace=workspace,
                service_account=new_collaborator,
                role_id=collaborator_role.id,
            )

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

        try:
            collaborator = Collaborator.objects.select_related(
                "workspace", "user", "service_account"
            ).get(
                Q(user__email=data.email) | Q(service_account__email=data.email),
                workspace=workspace,
            )
        except Collaborator.DoesNotExist:
            raise HttpError(400, f"No collaborator with email '{data.email}' found")

        if not principal.can_edit(collaborator):
            raise HttpError(
                403, "You do not have permission to modify this collaborator's role"
            )

        if data.role_id:
            collaborator_role = role_service.get_role_for_action(
                principal=principal,
                uid=data.role_id,
                action="view",
                expand_related=True,
            )

            if collaborator_role.workspace and collaborator_role.workspace != workspace:
                raise HttpError(400, "Role does not belong to the workspace")

            collaborator.role = collaborator_role

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

        try:
            collaborator = Collaborator.objects.select_related(
                "workspace", "user", "service_account"
            ).get(
                Q(user__email=data.email) | Q(service_account__email=data.email),
                workspace=workspace,
            )
        except Collaborator.DoesNotExist:
            raise HttpError(400, f"No collaborator with email '{data.email}' found")

        if not principal.can_delete(collaborator) and getattr(
            principal, "email", None
        ) != getattr(collaborator.user, "email", None):
            raise HttpError(
                403, "You do not have permission to remove this collaborator"
            )

        collaborator.delete()

        return "Collaborator removed from workspace"
