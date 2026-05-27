import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from core.types import Unset
from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.etl.services.data_connection import DataConnectionService
from interfaces.api.schemas import (
    DataConnectionResponse,
    DataConnectionPostBody,
    DataConnectionPatchBody,
    DataConnectionQueryParameters,
)

data_connection_router = Router(tags=["ETL Data Connections"])
data_connection_service = DataConnectionService()


@data_connection_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[DataConnectionResponse],
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

    with raise_http_errors():
        count, data_connections = data_connection_service.get_collection(
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by"}),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, data_connections


@data_connection_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: DataConnectionResponse,
        400: str,
        401: str,
        403: str,
        409: str,
        422: str,
    },
    by_alias=True,
)
def create_data_connection(
    request: HydroServerHttpRequest,
    data: DataConnectionPostBody,
):
    """
    Create a new ETL Data Connection.
    """

    with raise_http_errors():
        data_connection = data_connection_service.create(
            principal=request.principal,
            workspace=data.workspace_id,
            **data.model_dump(exclude_unset=True,
                              exclude={"workspace_id", "payload", "placeholder_variables",
                                       "notification"}),
            **data.payload.model_dump(exclude_unset=True),
            placeholder_variables=[
                pv.model_dump(exclude_unset=True)
                for pv in data.placeholder_variables
            ],
            **({"notification_recipient_emails": data.notification.recipient_emails,
                **{f"notification_{k}": v
                   for k, v in data.notification.schedule.model_dump(exclude_unset=True).items()}}
               if data.notification is not None else {}),
        )

    return 201, data_connection


@data_connection_router.get(
    "/{data_connection_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataConnectionResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
):
    """
    Get an ETL Data Connection.
    """

    with raise_http_errors():
        data_connection = data_connection_service.get(
            principal=request.principal,
            data_connection=data_connection_id,
        )

    return 200, data_connection


@data_connection_router.patch(
    "/{data_connection_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataConnectionResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def update_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
    data: DataConnectionPatchBody,
):
    """
    Update an ETL Data Connection.
    """

    with raise_http_errors():
        data_connection = data_connection_service.update(
            data_connection=data_connection_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True, exclude={"payload", "placeholder_variables",
                                                           "notification"}),
            **(data.payload.model_dump(exclude_unset=True) if "payload" in data.model_fields_set else {}),
            **({
                   "placeholder_variables": [
                       pv.model_dump(exclude_unset=True) for pv in data.placeholder_variables
                   ]
               } if "placeholder_variables" in data.model_fields_set else {}),
            **({"notification_recipient_emails": getattr(data.notification, "recipient_emails", []),
                **({f"notification_{k}": v
                    for k, v in data.notification.schedule.model_dump(exclude_unset=True).items()}
                   if getattr(data.notification, "schedule", Unset) is not Unset else {})}
               if "notification" in data.model_fields_set else {}),
        )

    return 200, data_connection


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
def delete_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
):
    """
    Delete an ETL Data Connection.
    """

    with raise_http_errors():
        data_connection_service.delete(
            principal=request.principal,
            data_connection=data_connection_id
        )

    return 204, None
