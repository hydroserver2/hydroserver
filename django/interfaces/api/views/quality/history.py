import uuid
from typing import Optional

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.quality.services.history import QCHistoryService
from interfaces.api.schemas.quality.history import (
    QualityControlHistorySummaryResponse,
    QualityControlHistoryDetailResponse,
    QualityControlHistoryQueryParameters,
    QualityControlHistoryPostBody,
)

_auth = [session_auth, bearer_auth, apikey_auth]

qc_history_router = Router(tags=["Quality Control Histories"])
qc_history_service = QCHistoryService()


@qc_history_router.get(
    "",
    auth=_auth,
    response={
        200: list[QualityControlHistorySummaryResponse] | list[QualityControlHistoryDetailResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_qc_histories(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[QualityControlHistoryQueryParameters],
):
    """Get QC histories. Returns detail responses (with expanded datastreams) when expand_related=True."""

    with raise_http_errors():
        count, histories = qc_history_service.get_collection(
            principal=request.principal,
            **query.model_dump(exclude_unset=True),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    if query.expand_related:
        return 200, [QualityControlHistoryDetailResponse.model_validate(history) for history in histories]

    return 200, [QualityControlHistorySummaryResponse.model_validate(history) for history in histories]


@qc_history_router.post(
    "",
    auth=_auth,
    response={201: QualityControlHistoryDetailResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_qc_history(
    request: HydroServerHttpRequest,
    data: QualityControlHistoryPostBody,
):
    """Create a new QC history for a managed datastream."""

    with raise_http_errors():
        history = qc_history_service.create(
            principal=request.principal,
            managed_datastream=data.managed_datastream_id,
            source_datastream=data.source_datastream_id,
        )

    return 201, history


@qc_history_router.get(
    "/{history_id}",
    auth=_auth,
    response={
        200: QualityControlHistorySummaryResponse | QualityControlHistoryDetailResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_qc_history(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """Get a QC history by ID."""

    with raise_http_errors():
        history = qc_history_service.get(
            history=history_id, principal=request.principal, expand_related=expand_related
        )

    if expand_related:
        return 200, QualityControlHistoryDetailResponse.model_validate(history)

    return 200, QualityControlHistorySummaryResponse.model_validate(history)


@qc_history_router.delete(
    "/{history_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_qc_history(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
):
    """Delete a QC history and all associated sessions."""

    with raise_http_errors():
        qc_history_service.delete(history=history_id, principal=request.principal)

    return 204, None
