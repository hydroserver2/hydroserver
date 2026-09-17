import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.iam import WorkspaceAPIService
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.schemas import (
    WorkspaceResponse,
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
    WorkspaceQueryParameters,
    WorkspaceItemQueryParameters,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)
from interfaces.api.views.iam.service_account import service_account_router
from interfaces.api.views.iam.collaborator import collaborator_router

workspace_router = Router(tags=["Workspaces"])
workspace_service = WorkspaceAPIService()


@workspace_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[WorkspaceResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_workspaces(
    request: HydroServerHttpRequest,
    query: Query[WorkspaceQueryParameters],
):
    """
    Get public workspaces and workspaces associated with the authenticated user.
    """

    return 200, workspace_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@workspace_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_workspace(
    request: HydroServerHttpRequest,
    data: WorkspacePostBody,
):
    """
    Create a new workspace owned by the authenticated user.
    """

    return 201, workspace_service.create(principal=request.principal, data=data)


@workspace_router.get(
    "/{workspace_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[WorkspaceResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_workspace(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    query: Query[WorkspaceItemQueryParameters],
):
    """
    Get workspace details.
    """

    return 200, workspace_service.get(
        principal=request.principal, uid=workspace_id, include=query.include
    )


@workspace_router.patch(
    "/{workspace_id}",
    auth=[session_auth, oidc_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_workspace(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    data: WorkspacePatchBody,
):
    """
    Update a workspace owned by the authenticated user.
    """

    workspace_service.update(
        principal=request.principal,
        uid=workspace_id,
        data=data,
    )

    return 204, None


@workspace_router.delete(
    "/{workspace_id}",
    auth=[session_auth, oidc_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_workspace(request: HydroServerHttpRequest, workspace_id: Path[uuid.UUID]):
    """
    Delete a workspace owned by the authenticated user.
    """

    return 204, workspace_service.delete(principal=request.principal, uid=workspace_id)


@workspace_router.post(
    "/{workspace_id}/transfer",
    auth=[session_auth, oidc_auth, basic_auth],
    response={
        201: str,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def transfer_workspace(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    data: WorkspaceTransferBody,
):
    """
    Transfer a workspace owned by the authenticated user to another HydroServer user.
    """

    return 201, workspace_service.transfer(
        principal=request.principal, uid=workspace_id, data=data
    )


@workspace_router.put(
    "/{workspace_id}/transfer",
    auth=[session_auth, oidc_auth, basic_auth],
    response={
        200: str,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def accept_workspace_transfer(
    request: HydroServerHttpRequest, workspace_id: Path[uuid.UUID]
):
    """
    Accept a pending workspace transfer.
    """

    return 200, workspace_service.accept_transfer(
        principal=request.principal, uid=workspace_id
    )


@workspace_router.delete(
    "/{workspace_id}/transfer",
    auth=[session_auth, oidc_auth, basic_auth],
    response={
        200: str,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def reject_workspace_transfer(
    request: HydroServerHttpRequest, workspace_id: Path[uuid.UUID]
):
    """
    Reject a pending workspace transfer.
    """

    return 200, workspace_service.reject_transfer(
        principal=request.principal, uid=workspace_id
    )


workspace_router.add_router(
    "{workspace_id}/collaborators", collaborator_router, tags=["Collaborators"]
)
workspace_router.add_router(
    "{workspace_id}/service-accounts", service_account_router, tags=["Service Accounts"]
)
