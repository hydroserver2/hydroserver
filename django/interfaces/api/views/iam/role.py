import uuid
from typing import Optional
from ninja import Router, Path, Query
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas import (
    RoleSummaryResponse,
    RoleDetailResponse,
    RoleQueryParameters,
    PaginatedResponse,
)
from interfaces.api.services.iam import RoleAPIService

role_router = Router(tags=["Roles"])
role_service = RoleAPIService()


@role_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[RoleSummaryResponse] | PaginatedResponse[RoleDetailResponse],
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
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@role_router.get(
    "/{role_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: RoleSummaryResponse | RoleDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_role(
    request: HydroServerHttpRequest,
    role_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get a Role.
    """

    return 200, role_service.get(
        principal=request.principal, uid=role_id, expand_related=expand_related
    )
