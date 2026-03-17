import uuid
from typing import Optional
from ninja import Router, Path, Query
from django.http import HttpResponse
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth, anonymous_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import (
    RoleSummaryResponse,
    RoleDetailResponse,
    RoleQueryParameters,
)
from domains.iam.services import RoleService

role_router = Router(tags=["Roles"])
role_service = RoleService()


@role_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[RoleSummaryResponse] | list[RoleDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_roles(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[RoleQueryParameters],
):
    """
    Get public Roles and Roles associated with the authenticated user.
    """

    return 200, role_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@role_router.get(
    "/{role_id}",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
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
