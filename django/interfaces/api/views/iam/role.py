import uuid

from ninja import Router, Path, Query

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.services.iam import RoleAPIService
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas import (
    RoleResponse,
    RoleQueryParameters,
    RoleItemQueryParameters,
    PaginatedResponse,
    ItemResponse,
)

role_router = Router(tags=["Roles"])
role_service = RoleAPIService()


@role_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[RoleResponse],
        401: str,
    },
    by_alias=True,
)
def get_roles(
    request: HydroServerHttpRequest,
    query: Query[RoleQueryParameters],
):
    """
    Get public Roles and Roles associated with the authenticated user.
    """

    return 200, role_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
    )


@role_router.get(
    "/{role_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[RoleResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_role(
    request: HydroServerHttpRequest,
    role_id: Path[uuid.UUID],
    query: Query[RoleItemQueryParameters],
):
    """
    Get a Role.
    """

    return 200, role_service.get(principal=request.principal, uid=role_id)
