import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import MethodAPIService
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    MethodResponse,
    MethodQueryParameters,
    MethodItemQueryParameters,
    MethodPostBody,
    MethodPatchBody,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

method_router = Router(tags=["Methods"])
method_service = MethodAPIService()


@method_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[MethodResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_methods(
    request: HydroServerHttpRequest,
    query: Query[MethodQueryParameters],
):
    """
    Get public Methods and Methods associated with the authenticated user.
    """

    return 200, method_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@method_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_method(
    request: HydroServerHttpRequest,
    data: MethodPostBody,
):
    """
    Create a new Method.
    """

    return 201, method_service.create(
        principal=request.principal,
        data=data,
    )


@method_router.get("types", response={200: PaginatedResponse[str]}, by_alias=True)
def get_types(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get method types.
    """

    return 200, method_service.list_types(
        offset=query.offset,
        limit=query.limit,
        sort_desc=query.sort_desc,
    )


@method_router.get(
    "/{method_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[MethodResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_method(
    request: HydroServerHttpRequest,
    method_id: Path[uuid.UUID],
    query: Query[MethodItemQueryParameters],
):
    """
    Get a Method.
    """

    return 200, method_service.get(
        principal=request.principal,
        uid=method_id,
        include=query.include,
    )


@method_router.patch(
    "/{method_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_method(
    request: HydroServerHttpRequest,
    method_id: Path[uuid.UUID],
    data: MethodPatchBody,
):
    """
    Update a Method.
    """

    method_service.update(
        principal=request.principal,
        uid=method_id,
        data=data,
    )

    return 204, None


@method_router.delete(
    "/{method_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_method(request: HydroServerHttpRequest, method_id: Path[uuid.UUID]):
    """
    Delete a Method.
    """

    return 204, method_service.delete(principal=request.principal, uid=method_id)
