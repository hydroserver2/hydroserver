import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.quality.history import QCHistoryAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.quality.history import (
    QualityControlHistoryResponse,
    QualityControlHistoryQueryParameters,
    QualityControlHistoryItemQueryParameters,
    QualityControlHistoryPostBody,
)

qc_history_router = Router(tags=["Quality Control Histories"])
qc_history_service = QCHistoryAPIService()


@qc_history_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[QualityControlHistoryResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_qc_histories(
    request: HydroServerHttpRequest,
    query: Query[QualityControlHistoryQueryParameters],
):
    """Get QC histories."""

    return 200, qc_history_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@qc_history_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={201: CreatedResponse, 400: str, 401: str, 403: str, 404: str},
    by_alias=True,
)
def create_qc_history(
    request: HydroServerHttpRequest,
    data: QualityControlHistoryPostBody,
):
    """Create a new QC history for a managed datastream."""

    return 201, qc_history_service.create(principal=request.principal, data=data)


@qc_history_router.get(
    "/{history_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[QualityControlHistoryResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_qc_history(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    query: Query[QualityControlHistoryItemQueryParameters],
):
    """Get a QC history by ID."""

    return 200, qc_history_service.get(
        principal=request.principal, uid=history_id, include=query.include
    )


@qc_history_router.delete(
    "/{history_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_qc_history(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
):
    """Delete a QC history and all associated sessions."""

    qc_history_service.delete(principal=request.principal, uid=history_id)

    return 204, None
