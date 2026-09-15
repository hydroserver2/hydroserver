import uuid

from typing import Optional, get_args
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.utils import IntegrityError

from core.iam.models import Workspace, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.service import APIService
from interfaces.api.http.errors import BadRequestError, ConflictError, PermissionDeniedError
from interfaces.api.schemas import (
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
)
from interfaces.api.schemas.iam.workspace import (
    WORKSPACE_INCLUDE_RELATIONS,
    WorkspaceSortByFields,
)

User = get_user_model()


class WorkspaceAPIService(APIService):
    INCLUDE_RELATIONS = WORKSPACE_INCLUDE_RELATIONS

    @staticmethod
    def attach_role_and_transfer_fields(
        workspace: Workspace, principal: User | ServiceAccount | AnonymousPrincipal
    ):
        if workspace.transfer and (
            workspace.transfer.new_owner == principal or workspace.owner == principal
        ):
            workspace.pending_transfer_to = workspace.transfer.new_owner

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
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        queryset = Workspace.objects

        if isinstance(principal, User):
            principal.collaborator_roles = list(
                principal.collaborations.select_related("role", "workspace")
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
                        # Workspaces this principal owns, collaborates on, or has
                        # a pending transfer to.
                        if isinstance(principal, User):
                            queryset = queryset.filter(
                                Q(owner=principal)
                                | Q(collaborators__user=principal)
                                | Q(transfer_confirmation__new_owner=principal)
                            )
                        elif isinstance(principal, ServiceAccount):
                            queryset = queryset.filter(pk=principal.workspace_id)
                        else:
                            queryset = queryset.none()
                else:
                    queryset = self.apply_filters(queryset, field, filtering[field])

        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(WorkspaceSortByFields)),
        )

        queryset = queryset.select_related(
            "owner", "transfer_confirmation", "transfer_confirmation__new_owner"
        )

        permitted_queryset = principal.filter_by_permission(queryset, "can_view")
        if filtering.get("is_associated") is True and isinstance(principal, User):
            # A transfer recipient must be able to discover the workspace 
            # to accept or reject it, even though they do not have the
            # workspace's normal view permission yet.
            permitted_queryset = permitted_queryset | queryset.filter(
                transfer_confirmation__new_owner=principal
            )

        queryset = permitted_queryset.distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)

        workspaces = [
            self.attach_role_and_transfer_fields(workspace, principal)
            for workspace in queryset
        ]

        return {
            "data": workspaces,
            "meta": meta,
            "included": self.resolve_includes(
                workspaces, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        workspace, _ = self.get_workspace(principal=principal, workspace_id=uid)

        if isinstance(principal, User):
            principal.collaborator_roles = list(
                principal.collaborations.select_related("role", "workspace")
                .prefetch_related("role__permissions")
                .all()
            )

        workspace = self.attach_role_and_transfer_fields(workspace, principal)

        return {
            "data": workspace,
            "included": self.resolve_includes(
                [workspace], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: WorkspacePostBody,
    ):
        if not isinstance(principal, User):
            raise PermissionDeniedError(
                "You do not have permission to create this workspace"
            )

        workspace = Workspace(pk=data.id, owner=principal, **data.dict())
        workspace.full_clean()

        try:
            workspace.save()
        except IntegrityError:
            raise ConflictError(
                "Workspace name or ID conflicts with an owned workspace"
            )

        return {"id": workspace.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: WorkspacePatchBody,
    ):
        workspace, _ = self.get_workspace(principal=principal, workspace_id=uid)

        if not principal.can_edit(workspace):
            raise PermissionDeniedError(
                "You do not have permission to edit this workspace"
            )

        workspace_body = data.dict(exclude_unset=True)

        for field, value in workspace_body.items():
            setattr(workspace, field, value)

        workspace.full_clean()

        try:
            workspace.save()
        except IntegrityError:
            raise ConflictError("Workspace name conflicts with an owned workspace")

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        workspace, _ = self.get_workspace(principal=principal, workspace_id=uid)

        if not principal.can_delete(workspace):
            raise PermissionDeniedError(
                "You do not have permission to delete this workspace"
            )

        workspace.delete()

        return "Workspace deleted"

    def transfer(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: WorkspaceTransferBody,
    ):
        workspace, _ = self.get_workspace(principal=principal, workspace_id=uid)

        if not principal.can_edit(workspace):
            raise PermissionDeniedError(
                "You do not have permission to transfer this workspace"
            )

        try:
            new_owner = User.objects.get(email=data.new_owner)
        except User.DoesNotExist:
            raise BadRequestError(f"No account with email '{data.new_owner}' found")

        workspace.initiate_transfer(new_owner)

        return "Workspace transfer initiated"

    def accept_transfer(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=uid, override_view_permissions=True
        )

        if not workspace.transfer:
            raise BadRequestError("No workspace transfer is pending")

        if workspace.transfer.new_owner != principal:
            raise PermissionDeniedError(
                "You do not have permission to accept this workspace transfer"
            )

        workspace.accept_transfer()

        return "Workspace transfer accepted"

    def reject_transfer(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=uid, override_view_permissions=True
        )

        if not workspace.transfer:
            raise BadRequestError("No workspace transfer is pending")

        if not (
            workspace.transfer.new_owner == principal or workspace.owner == principal
        ):
            raise PermissionDeniedError(
                "You do not have permission to reject this workspace transfer"
            )

        workspace.reject_transfer()

        return "Workspace transfer rejected"
