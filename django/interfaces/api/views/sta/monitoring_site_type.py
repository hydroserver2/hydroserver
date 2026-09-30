import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import MonitoringSiteTypeAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.vocabulary import (
    VocabularyQueryParameters,
    VocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.monitoring_site_type import (
    MonitoringSiteTypeResponse,
    MonitoringSiteTypePostBody,
    MonitoringSiteTypePatchBody,
)

monitoring_site_type_router = Router(tags=["Monitoring Site Types"])
monitoring_site_type_service = MonitoringSiteTypeAPIService()


@monitoring_site_type_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[MonitoringSiteTypeResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_monitoring_site_types(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get Monitoring Site Types.
    """

    return 200, monitoring_site_type_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
    )


@monitoring_site_type_router.post(
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
def create_monitoring_site_type(
    request: HydroServerHttpRequest,
    data: MonitoringSiteTypePostBody,
):
    """
    Create a new Monitoring Site Type.
    """

    return 201, monitoring_site_type_service.create(
        principal=request.principal,
        data=data,
    )


@monitoring_site_type_router.get(
    "/{monitoring_site_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[MonitoringSiteTypeResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_monitoring_site_type(
    request: HydroServerHttpRequest,
    monitoring_site_type_id: Path[uuid.UUID],
    query: Query[VocabularyItemQueryParameters],
):
    """
    Get a Monitoring Site Type.
    """

    return 200, monitoring_site_type_service.get(
        principal=request.principal,
        uid=monitoring_site_type_id,
    )


@monitoring_site_type_router.patch(
    "/{monitoring_site_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_monitoring_site_type(
    request: HydroServerHttpRequest,
    monitoring_site_type_id: Path[uuid.UUID],
    data: MonitoringSiteTypePatchBody,
):
    """
    Update a Monitoring Site Type.
    """

    monitoring_site_type_service.update(
        principal=request.principal,
        uid=monitoring_site_type_id,
        data=data,
    )
    return 204, None


@monitoring_site_type_router.delete(
    "/{monitoring_site_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_monitoring_site_type(
    request: HydroServerHttpRequest, monitoring_site_type_id: Path[uuid.UUID]
):
    """
    Delete a Monitoring Site Type.
    """

    return 204, monitoring_site_type_service.delete(
        principal=request.principal, uid=monitoring_site_type_id
    )
