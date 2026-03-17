import uuid
from typing import Optional, get_args
from ninja.errors import HttpError
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from domains.iam.models import Workspace, WorkspaceTransferConfirmation, APIKey
from interfaces.api.schemas import (
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
)
from interfaces.api.schemas.workspace import WorkspaceOrderByFields
from interfaces.api.service import ServiceUtils

User = get_user_model()


class WorkspaceService(ServiceUtils):
    @staticmethod
    def attach_role_and_transfer_fields(
        workspace: Workspace, principal: Optional[User | APIKey]
    ):
        if not principal:
            return workspace

        if workspace.transfer_details and (
            workspace.transfer_details.new_owner == principal
            or workspace.owner == principal
        ):
            workspace.pending_transfer_to = workspace.transfer_details.new_owner

        if hasattr(principal, "collaborator_roles"):
            collaborator = next(
                (
                    i
                    for i in principal.collaborator_roles
                    if i.user == principal and i.workspace == workspace
                ),
                None,
            )

            if collaborator:
                workspace.collaborator_role = collaborator.role

        return workspace

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
        queryset = Workspace.objects

        if isinstance(principal, User) and expand_related:
            principal.collaborator_roles = list(
                principal.workspace_roles.select_related("role", "workspace")
                .prefetch_related("role__permissions")
                .all()
            )

        for field in [
            "is_associated",
            "is_private",
        ]:
            if field in filtering:
                if field == "is_associated":
                    if filtering[field] is True:
                        queryset = queryset.associated(principal=principal)
                else:
                    queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(WorkspaceOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = queryset.select_related(
                "owner", "transfer_confirmation", "transfer_confirmation__new_owner"
            )

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        if expand_related:
            queryset = [
                self.attach_role_and_transfer_fields(workspace, principal)
                for workspace in queryset
            ]

        return [
            (
                WorkspaceDetailResponse.model_validate(workspace)
                if expand_related
                else WorkspaceSummaryResponse.model_validate(workspace)
            )
            for workspace in queryset
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(principal=principal, workspace_id=uid)

        if expand_related:
            if isinstance(principal, User):
                principal.collaborator_roles = list(principal.workspace_roles.all())

            workspace = self.attach_role_and_transfer_fields(workspace, principal)

        return (
            WorkspaceDetailResponse.model_validate(workspace)
            if expand_related
            else WorkspaceSummaryResponse.model_validate(workspace)
        )

    def create(
        self,
        principal: User,
        data: WorkspacePostBody,
        expand_related: Optional[bool] = None,
    ):
        if not Workspace.can_principal_create(principal):
            raise HttpError(403, "You do not have permission to create this workspace")

        try:
            workspace = Workspace.objects.create(
                pk=data.id, owner=principal, **data.dict()
            )
        except IntegrityError:
            raise HttpError(
                409, "Workspace name or ID conflicts with an owned workspace"
            )

        return self.get(principal, uid=workspace.id, expand_related=expand_related)

    def update(
        self,
        principal: User,
        uid: uuid.UUID,
        data: WorkspacePatchBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, permissions = self.get_workspace(
            principal=principal, workspace_id=uid
        )

        if "edit" not in permissions:
            raise HttpError(403, "You do not have permission to edit this workspace")

        workspace_body = data.dict(exclude_unset=True)

        for field, value in workspace_body.items():
            setattr(workspace, field, value)

        try:
            workspace.save()
        except IntegrityError:
            raise HttpError(409, "Workspace name conflicts with an owned workspace")

        return self.get(principal, uid=workspace.id, expand_related=expand_related)

    def delete(self, principal: User, uid: uuid.UUID):
        workspace, permissions = self.get_workspace(
            principal=principal, workspace_id=uid
        )

        if "delete" not in permissions:
            raise HttpError(403, "You do not have permission to delete this workspace")

        workspace.delete()

        return "Workspace deleted"

    def transfer(self, principal: User, uid: uuid.UUID, data: WorkspaceTransferBody):
        workspace, permissions = self.get_workspace(
            principal=principal, workspace_id=uid
        )

        if "edit" not in permissions:
            raise HttpError(
                403, "You do not have permission to transfer this workspace"
            )

        if workspace.transfer_details:
            raise HttpError(400, "Workspace transfer is already pending")

        try:
            new_owner = User.objects.get(email=data.new_owner)
        except User.DoesNotExist:
            raise HttpError(400, f"No account with email '{data.new_owner}' found")

        if not Workspace.can_principal_create(new_owner):
            raise HttpError(
                400,
                f"Workspace cannot be transferred to user '{data.new_owner}. User does not have permissions required to create a workspace.'",
            )

        if workspace.owner == new_owner:
            raise HttpError(400, f"Workspace already owned by user '{data.new_owner}'")

        WorkspaceTransferConfirmation.objects.create(
            workspace=workspace, new_owner=new_owner, initiated=timezone.now()
        )

        return "Workspace transfer initiated"

    def accept_transfer(self, principal: User, uid: uuid.UUID):
        workspace, permissions = self.get_workspace(
            principal=principal, workspace_id=uid, override_view_permissions=True
        )

        if "view" not in permissions:
            raise HttpError(404, "Workspace does not exist")

        if not workspace.transfer_details:
            raise HttpError(400, "No workspace transfer is pending")

        if workspace.transfer_details.new_owner != principal:
            raise HttpError(
                403, "You do not have permission to accept this workspace transfer"
            )

        workspace.owner = principal

        try:
            workspace.save()
        except IntegrityError:
            raise HttpError(409, "Workspace name conflicts with an owned workspace")

        workspace.transfer_details.delete()

        return "Workspace transfer accepted"

    def reject_transfer(self, principal: User, uid: uuid.UUID):
        workspace, permissions = self.get_workspace(
            principal=principal, workspace_id=uid, override_view_permissions=True
        )

        if "view" not in permissions:
            raise HttpError(404, "Workspace does not exist")

        if not workspace.transfer_details:
            raise HttpError(400, "No workspace transfer is pending")

        if not (
            workspace.transfer_details.new_owner == principal
            or workspace.owner == principal
        ):
            raise HttpError(
                403, "You do not have permission to reject this workspace transfer"
            )

        workspace.transfer_details.delete()

        return "Workspace transfer rejected"
