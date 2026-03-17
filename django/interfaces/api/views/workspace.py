import uuid
from typing import Optional
from ninja import Router, Path, Query
from django.db import transaction
from django.http import HttpResponse
from interfaces.http.request import HydroServerHttpRequest
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth, anonymous_auth
from interfaces.api.schemas import (
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
    WorkspaceQueryParameters,
)
from domains.iam.services import WorkspaceService
from interfaces.api.views.api_key import api_key_router
from interfaces.api.views.collaborator import collaborator_router

workspace_router = Router(tags=["Workspaces"])
workspace_service = WorkspaceService()


@workspace_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[WorkspaceDetailResponse] | list[WorkspaceSummaryResponse],
        401: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_workspaces(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[WorkspaceQueryParameters],
):
    """
    Get public workspaces and workspaces associated with the authenticated user.
    """

    return 200, workspace_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=True if query.expand_related is None else query.expand_related,
    )


@workspace_router.post(
    "",
    auth=[session_auth, bearer_auth],
    response={
        201: WorkspaceDetailResponse | WorkspaceSummaryResponse,
        401: str,
        422: str,
    },
    by_alias=True,
    exclude_unset=True,
)
@transaction.atomic
def create_workspace(
    request: HydroServerHttpRequest,
    data: WorkspacePostBody,
    expand_related: Optional[bool] = True,
):
    """
    Create a new workspace owned by the authenticated user.
    """

    return 201, workspace_service.create(
        principal=request.principal, data=data, expand_related=expand_related
    )


@workspace_router.get(
    "/{workspace_id}",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: WorkspaceDetailResponse | WorkspaceSummaryResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_workspace(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    expand_related: Optional[bool] = True,
):
    """
    Get workspace details.
    """

    return 200, workspace_service.get(
        principal=request.principal, uid=workspace_id, expand_related=expand_related
    )


@workspace_router.patch(
    "/{workspace_id}",
    auth=[session_auth, bearer_auth],
    response={
        200: WorkspaceDetailResponse | WorkspaceSummaryResponse,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
    exclude_unset=True,
)
@transaction.atomic
def update_workspace(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    data: WorkspacePatchBody,
    expand_related: Optional[bool] = True,
):
    """
    Update a workspace owned by the authenticated user.
    """

    return 200, workspace_service.update(
        principal=request.principal,
        uid=workspace_id,
        data=data,
        expand_related=expand_related,
    )


@workspace_router.delete(
    "/{workspace_id}",
    auth=[session_auth, bearer_auth],
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
    auth=[session_auth, bearer_auth],
    response={
        201: str,
        400: str,
        401: str,
        403: str,
        422: str,
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
    auth=[session_auth, bearer_auth],
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
    auth=[session_auth, bearer_auth],
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


workspace_router.add_router("{workspace_id}/collaborators", collaborator_router)
workspace_router.add_router("{workspace_id}/api-keys", api_key_router)
