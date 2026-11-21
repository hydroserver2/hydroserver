import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.auth.security import session_auth, oidc_data_read_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ObservationAPIService
from interfaces.api.schemas import (
    ObservationResponse,
    ObservationItemQueryParameters,
    ObservationRowResponse,
    ObservationColumnResponse,
    LatestObservationQueryParameters,
    PaginatedResponse,
    ItemResponse,
)

latest_observation_router = Router(tags=["Latest Observations"])
observation_service = ObservationAPIService()


@latest_observation_router.get(
    "/items",
    auth=[session_auth, oidc_data_read_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ObservationResponse]
        | PaginatedResponse[ObservationRowResponse]
        | PaginatedResponse[ObservationColumnResponse],
        400: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_latest_observations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[LatestObservationQueryParameters],
):
    """
    Get the latest observation of each datastream: one for a time series datastream, and one per z at the latest
    phenomenon time for a profile coverage datastream. Use `datastreamId` to get a single datastream's latest
    observation(s). `datetime` matches datastreams whose latest observation falls in the interval.
    """

    profile = getattr(request, "response_profile", None)

    return 200, observation_service.list(
        principal=request.principal,
        profile=profile.key if profile else None,
        response=response,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        properties=query.properties,
        include=query.include,
        bbox=query.bbox,
        datetime_interval=query.datetime,
        latest=True,
    )


@latest_observation_router.get(
    "/items/{observation_id}",
    auth=[session_auth, oidc_data_read_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ObservationResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_latest_observation(
    request: HydroServerHttpRequest,
    observation_id: Path[uuid.UUID],
    query: Query[ObservationItemQueryParameters],
):
    """
    Get a latest observation. Returns 404 once a newer observation replaces it as its datastream's latest.
    """

    return 200, observation_service.get_item(
        principal=request.principal,
        uid=observation_id,
        include=query.include,
        latest=True,
    )
