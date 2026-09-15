import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import UnitAPIService
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    UnitResponse,
    UnitPostBody,
    UnitPatchBody,
    UnitQueryParameters,
    UnitItemQueryParameters,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

unit_router = Router(tags=["Units"])
unit_service = UnitAPIService()


@unit_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[UnitResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_units(
    request: HydroServerHttpRequest,
    query: Query[UnitQueryParameters],
):
    """
    Get public Units and Units associated with the authenticated user.
    """

    return 200, unit_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@unit_router.post(
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
def create_unit(
    request: HydroServerHttpRequest,
    data: UnitPostBody,
):
    """
    Create a new Unit.
    """

    return 201, unit_service.create(
        principal=request.principal,
        data=data,
    )


@unit_router.get("/types", response={200: PaginatedResponse[str]}, by_alias=True)
def get_unit_types(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get unit types.
    """

    return 200, unit_service.list_unit_types(
        offset=query.offset,
        limit=query.limit,
        sort_desc=query.sort_desc,
    )


@unit_router.get(
    "/{unit_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[UnitResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_unit(
    request: HydroServerHttpRequest,
    unit_id: Path[uuid.UUID],
    query: Query[UnitItemQueryParameters],
):
    """
    Get a Unit.
    """

    return 200, unit_service.get(
        principal=request.principal,
        uid=unit_id,
        include=query.include,
    )


@unit_router.patch(
    "/{unit_id}",
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
def update_unit(
    request: HydroServerHttpRequest,
    unit_id: Path[uuid.UUID],
    data: UnitPatchBody,
):
    """
    Update a Unit.
    """

    unit_service.update(
        principal=request.principal,
        uid=unit_id,
        data=data,
    )

    return 204, None


@unit_router.delete(
    "/{unit_id}",
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
def delete_unit(request: HydroServerHttpRequest, unit_id: Path[uuid.UUID]):
    """
    Delete a Unit.
    """

    return 204, unit_service.delete(principal=request.principal, uid=unit_id)
