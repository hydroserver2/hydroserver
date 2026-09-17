import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ProcessingLevelAPIService
from interfaces.api.schemas import (
    ProcessingLevelResponse,
    ProcessingLevelQueryParameters,
    ProcessingLevelItemQueryParameters,
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

processing_level_router = Router(tags=["Processing Levels"])
processing_level_service = ProcessingLevelAPIService()


@processing_level_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ProcessingLevelResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_processing_levels(
    request: HydroServerHttpRequest,
    query: Query[ProcessingLevelQueryParameters],
):
    """
    Get public Processing Levels and Processing Levels associated with the authenticated user.
    """

    return 200, processing_level_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@processing_level_router.post(
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
def create_processing_level(
    request: HydroServerHttpRequest,
    data: ProcessingLevelPostBody,
):
    """
    Create a new Processing Level.
    """

    return 201, processing_level_service.create(
        principal=request.principal, data=data
    )


@processing_level_router.get(
    "/{processing_level_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ProcessingLevelResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_processing_level(
    request: HydroServerHttpRequest,
    processing_level_id: Path[uuid.UUID],
    query: Query[ProcessingLevelItemQueryParameters],
):
    """
    Get a Processing Level.
    """

    return 200, processing_level_service.get(
        principal=request.principal,
        uid=processing_level_id,
        include=query.include,
    )


@processing_level_router.patch(
    "/{processing_level_id}",
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
def update_processing_level(
    request: HydroServerHttpRequest,
    processing_level_id: Path[uuid.UUID],
    data: ProcessingLevelPatchBody,
):
    """
    Update a Processing Level.
    """

    processing_level_service.update(
        principal=request.principal,
        uid=processing_level_id,
        data=data,
    )

    return 204, None


@processing_level_router.delete(
    "/{processing_level_id}",
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
def delete_processing_level(
    request: HydroServerHttpRequest, processing_level_id: Path[uuid.UUID]
):
    """
    Delete a Processing Level.
    """

    return 204, processing_level_service.delete(
        principal=request.principal, uid=processing_level_id
    )
