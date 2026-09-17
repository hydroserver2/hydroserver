import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.etl.mapping import EtlMappingAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.etl.mapping import (
    EtlMappingResponse,
    EtlMappingPostBody,
    EtlMappingPatchBody,
    EtlMappingQueryParameters,
    EtlMappingItemQueryParameters,
)

etl_mapping_router = Router(tags=["ETL Mappings"])
_service = EtlMappingAPIService()


@etl_mapping_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[EtlMappingResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_mappings(
    request: HydroServerHttpRequest,
    query: Query[EtlMappingQueryParameters],
):
    """Get ETL mappings."""

    return 200, _service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@etl_mapping_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def create_etl_mapping(
    request: HydroServerHttpRequest,
    data: EtlMappingPostBody,
):
    """Create an ETL mapping."""

    return 201, _service.create(
        principal=request.principal,
        data=data,
    )


@etl_mapping_router.get(
    "/{mapping_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[EtlMappingResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_mapping(
    request: HydroServerHttpRequest,
    mapping_id: Path[uuid.UUID],
    query: Query[EtlMappingItemQueryParameters],
):
    """Get an ETL mapping."""

    return 200, _service.get(
        principal=request.principal,
        uid=mapping_id,
        include=query.include,
    )


@etl_mapping_router.patch(
    "/{mapping_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def update_etl_mapping(
    request: HydroServerHttpRequest,
    mapping_id: Path[uuid.UUID],
    data: EtlMappingPatchBody,
):
    """Update an ETL mapping."""

    _service.update(
        principal=request.principal,
        uid=mapping_id,
        data=data,
    )

    return 204, None


@etl_mapping_router.delete(
    "/{mapping_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_etl_mapping(
    request: HydroServerHttpRequest,
    mapping_id: Path[uuid.UUID],
):
    """Delete an ETL mapping."""

    _service.delete(
        principal=request.principal,
        uid=mapping_id,
    )

    return 204, None
