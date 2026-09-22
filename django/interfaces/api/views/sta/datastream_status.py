import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import DatastreamStatusAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.vocabulary import (
    VocabularyQueryParameters,
    VocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.datastream_status import (
    DatastreamStatusResponse,
    DatastreamStatusPostBody,
    DatastreamStatusPatchBody,
)

datastream_status_router = Router(tags=["Datastream Statuses"])
datastream_status_service = DatastreamStatusAPIService()


@datastream_status_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[DatastreamStatusResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_datastream_statuses(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get Datastream Statuses.
    """

    return 200, datastream_status_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
    )


@datastream_status_router.post(
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
def create_datastream_status(
    request: HydroServerHttpRequest,
    data: DatastreamStatusPostBody,
):
    """
    Create a new Datastream Status.
    """

    return 201, datastream_status_service.create(
        principal=request.principal,
        data=data,
    )


@datastream_status_router.get(
    "/{datastream_status_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[DatastreamStatusResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_datastream_status(
    request: HydroServerHttpRequest,
    datastream_status_id: Path[uuid.UUID],
    query: Query[VocabularyItemQueryParameters],
):
    """
    Get a Datastream Status.
    """

    return 200, datastream_status_service.get(
        principal=request.principal,
        uid=datastream_status_id,
    )


@datastream_status_router.patch(
    "/{datastream_status_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_datastream_status(
    request: HydroServerHttpRequest,
    datastream_status_id: Path[uuid.UUID],
    data: DatastreamStatusPatchBody,
):
    """
    Update a Datastream Status.
    """

    datastream_status_service.update(
        principal=request.principal,
        uid=datastream_status_id,
        data=data,
    )
    return 204, None


@datastream_status_router.delete(
    "/{datastream_status_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_datastream_status(
    request: HydroServerHttpRequest, datastream_status_id: Path[uuid.UUID]
):
    """
    Delete a Datastream Status.
    """

    return 204, datastream_status_service.delete(
        principal=request.principal, uid=datastream_status_id
    )
