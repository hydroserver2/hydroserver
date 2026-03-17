import uuid
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.request import HydroServerHttpRequest
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth
from domains.etl.services import DataConnectionService
from interfaces.api.schemas import (DataConnectionSummaryResponse, DataConnectionDetailResponse, DataConnectionPostBody,
                                    DataConnectionPatchBody, DataConnectionQueryParameters)


data_connection_router = Router(tags=["ETL Data Connections"])
data_connection_service = DataConnectionService()


@data_connection_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[DataConnectionSummaryResponse] | list[DataConnectionDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_data_connections(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[DataConnectionQueryParameters],
):
    """
    Get ETL Data Connections associated with the authenticated user.
    """

    return 200, data_connection_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@data_connection_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: DataConnectionDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def create_data_connection(
    request: HydroServerHttpRequest,
    data: DataConnectionPostBody
):
    """
    Create a new ETL Data Connection.
    """

    return 201, data_connection_service.create(
        principal=request.principal, data=data
    )


@data_connection_router.get(
    "/{data_connection_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataConnectionSummaryResponse | DataConnectionDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
    expand_related: bool | None = None,
):
    """
    Get an ETL Data Connection.
    """

    return 200, data_connection_service.get(
        principal=request.principal, uid=data_connection_id, expand_related=expand_related,
    )


@data_connection_router.patch(
    "/{data_connection_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataConnectionDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
    data: DataConnectionPatchBody,
):
    """
    Update a ETL Data Connection.
    """

    return 200, data_connection_service.update(
        principal=request.principal,
        uid=data_connection_id,
        data=data,
    )


@data_connection_router.delete(
    "/{data_connection_id}",
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
def delete_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
):
    """
    Delete an ETL Data Connection.
    """

    return 204, data_connection_service.delete(
        principal=request.principal, uid=data_connection_id
    )
