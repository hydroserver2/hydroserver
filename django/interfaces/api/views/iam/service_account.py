import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.iam import ServiceAccountAPIService
from interfaces.api.schemas import (
    ServiceAccountResponse,
    ServiceAccountQueryParameters,
    ServiceAccountItemQueryParameters,
    ServiceAccountPostBody,
    ServiceAccountPatchBody,
    ServiceAccountCreatedResponse,
    ServiceAccountKeyResponse,
    PaginatedResponse,
    ItemResponse,
)

service_account_router = Router(tags=["Service Accounts"])
service_account_service = ServiceAccountAPIService()


@service_account_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[ServiceAccountResponse],
        401: str,
    },
    by_alias=True,
)
def get_service_accounts(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    query: Query[ServiceAccountQueryParameters],
):
    """
    Get service accounts associated with the authenticated user.
    """

    return 200, service_account_service.list(
        principal=request.principal,
        workspace_id=workspace_id,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@service_account_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: ServiceAccountCreatedResponse,
        401: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_service_account(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    data: ServiceAccountPostBody,
):
    """
    Create a new service account for the workspace.
    """

    return 201, service_account_service.create(
        principal=request.principal,
        workspace_id=workspace_id,
        data=data,
    )


@service_account_router.get(
    "/{service_account_id}",
    auth=[session_auth, oidc_auth],
    response={
        200: ItemResponse[ServiceAccountResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_service_account(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    service_account_id: Path[uuid.UUID],
    query: Query[ServiceAccountItemQueryParameters],
):
    """
    Get service account details.
    """

    return 200, service_account_service.get(
        principal=request.principal,
        workspace_id=workspace_id,
        uid=service_account_id,
        include=query.include,
    )


@service_account_router.patch(
    "/{service_account_id}",
    auth=[session_auth, oidc_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_service_account(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    service_account_id: Path[uuid.UUID],
    data: ServiceAccountPatchBody,
):
    """
    Update a service account.
    """

    service_account_service.update(
        principal=request.principal,
        workspace_id=workspace_id,
        uid=service_account_id,
        data=data,
    )

    return 204, None


@service_account_router.delete(
    "/{service_account_id}",
    auth=[session_auth, oidc_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_service_account(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    service_account_id: Path[uuid.UUID],
):
    """
    Delete a service account.
    """

    return 204, service_account_service.delete(
        principal=request.principal, workspace_id=workspace_id, uid=service_account_id
    )


@service_account_router.put(
    "/{service_account_id}/regenerate",
    auth=[session_auth, oidc_auth],
    response={
        201: ServiceAccountKeyResponse,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def regenerate_service_account_key(
    request: HydroServerHttpRequest,
    workspace_id: Path[uuid.UUID],
    service_account_id: Path[uuid.UUID],
):
    """
    Regenerate a service account's key using existing settings.
    """

    return 201, service_account_service.regenerate(
        principal=request.principal,
        workspace_id=workspace_id,
        uid=service_account_id,
    )
