import uuid
from typing import Optional
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth, anonymous_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    SensorSummaryResponse,
    SensorDetailResponse,
    SensorQueryParameters,
    SensorPostBody,
    SensorPatchBody,
)
from domains.sta.services import SensorService

sensor_router = Router(tags=["Sensors"])
sensor_service = SensorService()


@sensor_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[SensorSummaryResponse] | list[SensorDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_sensors(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[SensorQueryParameters],
):
    """
    Get public Sensors and Sensors associated with the authenticated user.
    """

    return 200, sensor_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@sensor_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: SensorSummaryResponse | SensorDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_sensor(
    request: HydroServerHttpRequest,
    data: SensorPostBody,
    expand_related: Optional[bool] = None,
):
    """
    Create a new Sensor.
    """

    return 201, sensor_service.create(
        principal=request.principal,
        data=data,
        expand_related=expand_related,
    )


@sensor_router.get("encoding-types", response={200: list[str]}, by_alias=True)
def get_sensor_encoding_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get sensor encoding types.
    """

    return 200, sensor_service.list_encoding_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@sensor_router.get("method-types", response={200: list[str]}, by_alias=True)
def get_method_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get method types.
    """

    return 200, sensor_service.list_method_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@sensor_router.get(
    "/{sensor_id}",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: SensorSummaryResponse | SensorDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_sensor(
    request: HydroServerHttpRequest,
    sensor_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get a Sensor.
    """

    return 200, sensor_service.get(
        principal=request.principal, uid=sensor_id, expand_related=expand_related
    )


@sensor_router.patch(
    "/{sensor_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: SensorSummaryResponse | SensorDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_sensor(
    request: HydroServerHttpRequest,
    sensor_id: Path[uuid.UUID],
    data: SensorPatchBody,
    expand_related: Optional[bool] = None,
):
    """
    Update a Sensor.
    """

    return 200, sensor_service.update(
        principal=request.principal,
        uid=sensor_id,
        data=data,
        expand_related=expand_related,
    )


@sensor_router.delete(
    "/{sensor_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_sensor(request: HydroServerHttpRequest, sensor_id: Path[uuid.UUID]):
    """
    Delete a Sensor.
    """

    return 204, sensor_service.delete(principal=request.principal, uid=sensor_id)
