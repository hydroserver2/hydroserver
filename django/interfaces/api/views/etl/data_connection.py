import uuid

from ninja import Router, Path, Query

from core.types import Unset
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.etl.data_connection import DataConnectionAPIService
from interfaces.api.schemas import (
    DataConnectionResponse,
    DataConnectionPostBody,
    DataConnectionPatchBody,
    DataConnectionQueryParameters,
    DataConnectionItemQueryParameters,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

data_connection_router = Router(tags=["ETL Data Connections"])
data_connection_service = DataConnectionAPIService()


@data_connection_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[DataConnectionResponse],
        401: str,
    },
    by_alias=True,
)
def get_data_connections(
    request: HydroServerHttpRequest,
    query: Query[DataConnectionQueryParameters],
):
    """
    Get ETL Data Connections associated with the authenticated user.
    """

    return 200, data_connection_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@data_connection_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
        409: str,
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

    return 201, data_connection_service.create(
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


@data_connection_router.get(
    "/{data_connection_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[DataConnectionResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_connection(
    request: HydroServerHttpRequest,
    data_connection_id: Path[uuid.UUID],
    query: Query[DataConnectionItemQueryParameters],
):
    """
    Get an ETL Data Connection.
    """

    return 200, data_connection_service.get_item(
        principal=request.principal,
        uid=data_connection_id,
        include=query.include,
    )


@data_connection_router.patch(
    "/{data_connection_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
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

    data_connection_service.update(
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

    return 204, None


@data_connection_router.delete(
    "/{data_connection_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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

    data_connection_service.delete(
        principal=request.principal,
        data_connection=data_connection_id
    )

    return 204, None
