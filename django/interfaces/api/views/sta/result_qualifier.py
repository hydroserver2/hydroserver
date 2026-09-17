import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ResultQualifierAPIService
from interfaces.api.schemas import (
    ResultQualifierResponse,
    ResultQualifierQueryParameters,
    ResultQualifierItemQueryParameters,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

result_qualifier_router = Router(tags=["Result Qualifiers"])
result_qualifier_service = ResultQualifierAPIService()


@result_qualifier_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ResultQualifierResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_result_qualifiers(
    request: HydroServerHttpRequest,
    query: Query[ResultQualifierQueryParameters],
):
    """
    Get public Result Qualifiers and Result Qualifiers associated with the authenticated user.
    """

    return 200, result_qualifier_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@result_qualifier_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_result_qualifier(
    request: HydroServerHttpRequest,
    data: ResultQualifierPostBody,
):
    """
    Create a new Result Qualifier.
    """

    return 201, result_qualifier_service.create(
        principal=request.principal,
        data=data,
    )


@result_qualifier_router.get(
    "/{result_qualifier_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ResultQualifierResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_result_qualifier(
    request: HydroServerHttpRequest,
    result_qualifier_id: Path[uuid.UUID],
    query: Query[ResultQualifierItemQueryParameters],
):
    """
    Get a Result Qualifier.
    """

    return 200, result_qualifier_service.get(
        principal=request.principal,
        uid=result_qualifier_id,
        include=query.include,
    )


@result_qualifier_router.patch(
    "/{result_qualifier_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_result_qualifier(
    request: HydroServerHttpRequest,
    result_qualifier_id: Path[uuid.UUID],
    data: ResultQualifierPatchBody,
):
    """
    Update a Result Qualifier.
    """

    result_qualifier_service.update(
        principal=request.principal,
        uid=result_qualifier_id,
        data=data,
    )

    return 204, None


@result_qualifier_router.delete(
    "/{result_qualifier_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_result_qualifier(
    request: HydroServerHttpRequest, result_qualifier_id: Path[uuid.UUID]
):
    """
    Delete a Result Qualifier.
    """

    return 204, result_qualifier_service.delete(
        principal=request.principal, uid=result_qualifier_id
    )
