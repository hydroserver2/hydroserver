import uuid
from typing import Optional
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.auth.security import (
    session_auth,
    oidc_auth,
    apikey_auth,
    basic_auth,
    anonymous_auth,
)
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    MethodSummaryResponse,
    MethodDetailResponse,
    MethodQueryParameters,
    MethodPostBody,
    MethodPatchBody,
)
from interfaces.api.services.sta import MethodAPIService

method_router = Router(tags=["Methods"])
method_service = MethodAPIService()


@method_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: list[MethodSummaryResponse] | list[MethodDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_methods(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[MethodQueryParameters],
):
    """
    Get public Methods and Methods associated with the authenticated user.
    """

    return 200, method_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@method_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: MethodSummaryResponse | MethodDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_method(
    request: HydroServerHttpRequest,
    data: MethodPostBody,
    expand_related: Optional[bool] = None,
):
    """
    Create a new Method.
    """

    return 201, method_service.create(
        principal=request.principal,
        data=data,
        expand_related=expand_related,
    )


@method_router.get("types", response={200: list[str]}, by_alias=True)
def get_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get method types.
    """

    return 200, method_service.list_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@method_router.get(
    "/{method_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: MethodSummaryResponse | MethodDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_method(
    request: HydroServerHttpRequest,
    method_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get a Method.
    """

    return 200, method_service.get(
        principal=request.principal, uid=method_id, expand_related=expand_related
    )


@method_router.patch(
    "/{method_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: MethodSummaryResponse | MethodDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_method(
    request: HydroServerHttpRequest,
    method_id: Path[uuid.UUID],
    data: MethodPatchBody,
    expand_related: Optional[bool] = None,
):
    """
    Update a Method.
    """

    return 200, method_service.update(
        principal=request.principal,
        uid=method_id,
        data=data,
        expand_related=expand_related,
    )


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
