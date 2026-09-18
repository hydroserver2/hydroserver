import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import UnitTypeAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyQueryParameters,
    ControlledVocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.unit_type import (
    UnitTypeResponse,
    UnitTypePostBody,
    UnitTypePatchBody,
)

unit_type_router = Router(tags=["Unit Types"])
unit_type_service = UnitTypeAPIService()


@unit_type_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[UnitTypeResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_unit_types(
    request: HydroServerHttpRequest,
    query: Query[ControlledVocabularyQueryParameters],
):
    """
    Get public Unit Types and Unit Types associated with the authenticated user.
    """

    return 200, unit_type_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@unit_type_router.post(
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
def create_unit_type(
    request: HydroServerHttpRequest,
    data: UnitTypePostBody,
):
    """
    Create a new Unit Type.
    """

    return 201, unit_type_service.create(
        principal=request.principal,
        data=data,
    )


@unit_type_router.get(
    "/{unit_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[UnitTypeResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_unit_type(
    request: HydroServerHttpRequest,
    unit_type_id: Path[uuid.UUID],
    query: Query[ControlledVocabularyItemQueryParameters],
):
    """
    Get a Unit Type.
    """

    return 200, unit_type_service.get(
        principal=request.principal,
        uid=unit_type_id,
        include=query.include,
    )


@unit_type_router.patch(
    "/{unit_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_unit_type(
    request: HydroServerHttpRequest,
    unit_type_id: Path[uuid.UUID],
    data: UnitTypePatchBody,
):
    """
    Update a Unit Type.
    """

    unit_type_service.update(
        principal=request.principal,
        uid=unit_type_id,
        data=data,
    )
    return 204, None


@unit_type_router.delete(
    "/{unit_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_unit_type(
    request: HydroServerHttpRequest, unit_type_id: Path[uuid.UUID]
):
    """
    Delete a Unit Type.
    """

    return 204, unit_type_service.delete(
        principal=request.principal, uid=unit_type_id
    )
