import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from interfaces.api.schemas.quality.history import (
    QualityControlHistorySummaryResponse,
    QualityControlHistoryDetailResponse,
    QualityControlHistoryQueryParameters,
    QualityControlHistoryPostBody,
)

_auth = [session_auth, bearer_auth, apikey_auth]

qc_history_router = Router(tags=["Quality Control Histories"])


@qc_history_router.get(
    "",
    auth=_auth,
    response={
        200: list[QualityControlHistoryDetailResponse] | list[QualityControlHistorySummaryResponse],
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

    raise NotImplementedError


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

    raise NotImplementedError


@qc_history_router.get(
    "/{history_id}",
    auth=_auth,
    response={200: QualityControlHistoryDetailResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_qc_history(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
):
    """Get a QC history by ID."""

    raise NotImplementedError


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

    raise NotImplementedError
