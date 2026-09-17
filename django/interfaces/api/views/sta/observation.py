import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ObservationAPIService
from interfaces.api.schemas import (
    ObservationResponse,
    ObservationItemQueryParameters,
    ObservationRowResponse,
    ObservationColumnarResponse,
    ObservationQueryParameters,
    ObservationPostBody,
    ObservationBulkPostBody,
    ObservationBulkColumnarPostBody,
    ObservationBulkPostQueryParameters,
    ObservationBulkDeleteBody,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

observation_router = Router(tags=["Observations"])
observation_service = ObservationAPIService()


@observation_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ObservationResponse]
        | ObservationRowResponse
        | ObservationColumnarResponse,
        400: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_observations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[ObservationQueryParameters],
):
    """
    Get Observations.
    """

    return 200, observation_service.list(
        principal=request.principal,
        response=response,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        response_format=query.response_format,
        include=query.include,
    )


@observation_router.post(
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
def create_observation(
    request: HydroServerHttpRequest,
    data: ObservationPostBody,
):
    """
    Create a new Observation.
    """

    return 201, observation_service.create(
        principal=request.principal,
        datastream_id=data.datastream_id,
        data=data,
    )


@observation_router.post(
    "/bulk-create",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={201: None, 400: str, 403: str, 404: str},
)
@transaction.atomic
def insert_observations(
    request: HydroServerHttpRequest,
    query: Query[ObservationBulkPostQueryParameters],
    data: ObservationBulkPostBody | ObservationBulkColumnarPostBody,
):
    """
    Insert Observations.
    """

    return 201, observation_service.bulk_create(
        principal=request.principal,
        data=data,
        datastream_id=data.datastream_id,
        mode=query.mode or "append",
    )


@observation_router.post(
    "/bulk-delete",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 403: str, 404: str},
)
@transaction.atomic
def delete_observations(
    request: HydroServerHttpRequest,
    data: ObservationBulkDeleteBody,
):
    """
    Delete Observations between the given phenomenon start and end times.
    """

    return 204, observation_service.bulk_delete(
        principal=request.principal, datastream_id=data.datastream_id, data=data
    )


@observation_router.get(
    "/{observation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ObservationResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_observation(
    request: HydroServerHttpRequest,
    observation_id: Path[uuid.UUID],
    query: Query[ObservationItemQueryParameters],
):
    """
    Get an Observation.
    """

    return 200, observation_service.get_item(
        principal=request.principal,
        uid=observation_id,
        include=query.include,
    )


@observation_router.delete(
    "/{observation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_observation(
    request: HydroServerHttpRequest,
    observation_id: Path[uuid.UUID],
):
    """
    Delete an Observation.
    """

    return 204, observation_service.delete(
        principal=request.principal,
        uid=observation_id,
    )
