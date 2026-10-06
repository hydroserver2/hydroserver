import uuid

from typing import Optional, get_args
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q
from django.db.utils import IntegrityError

from core.iam.models import Workspace, ServiceAccount
from core.sta.models import MonitoringSite
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.service import APIService
from interfaces.api.http.errors import BadRequestError, ConflictError, PermissionDeniedError
from interfaces.api.schemas import (
    BoundingBox,
    TimeInterval,
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

    @classmethod
    def apply_visible_site_bbox(
        cls,
        principal: User | ServiceAccount | AnonymousPrincipal,
        queryset,
        bbox: Optional[BoundingBox],
    ):
        """
        Filters workspaces by the extent of the monitoring sites the principal can view, which
        is their GeoJSON geometry (interfaces/api/geometry.py). A workspace matches when that
        extent intersects the box, or when the principal can view none of its sites, since a
        workspace without a geometry matches any box. Sites the principal can't view never affect
        the result.

        The extent intersects the box when some visible site lies on or north of the box's
        south edge, some on or south of its north edge, and likewise for its east and west edges.
        """

        if bbox is None:
            return queryset

        visible_sites = principal.filter_by_permission(
            MonitoringSite.objects.filter(workspace_id=OuterRef("pk")), "can_view"
        )

        def any_site(**lookup):
            return Exists(visible_sites.filter(**lookup))

        latitudes = any_site(latitude__gte=bbox.south) & any_site(latitude__lte=bbox.north)
        if bbox.crosses_antimeridian:
            longitudes = any_site(longitude__gte=bbox.west) | any_site(longitude__lte=bbox.east)
        else:
            longitudes = any_site(longitude__gte=bbox.west) & any_site(longitude__lte=bbox.east)

        return queryset.filter((latitudes & longitudes) | ~Exists(visible_sites))

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
        bbox: Optional[BoundingBox] = None,
        datetime_interval: Optional[TimeInterval] = None,
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

        queryset = self.apply_visible_site_bbox(principal, queryset, bbox)
        queryset = self.apply_visible_datastream_datetime(
            principal, queryset, datetime_interval, "monitoring_site__workspace_id"
        )
        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(WorkspaceSortByFields)),
            rank=has_search,
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
