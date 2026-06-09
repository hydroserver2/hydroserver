import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from interfaces.api.schemas.quality.operation import (
    QualityControlOperationResponse,
    QualityControlOperationQueryParameters,
    QualityControlOperationPostBody,
    QualityControlOperationPatchBody,
)

_auth = [session_auth, bearer_auth, apikey_auth]

qc_operation_router = Router(tags=["Quality Control Operations"])


@qc_operation_router.get(
    "",
    auth=_auth,
    response={200: list[QualityControlOperationResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_qc_operations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    query: Query[QualityControlOperationQueryParameters],
):
    """Get all operations for a QC session in execution order."""

    raise NotImplementedError


@qc_operation_router.post(
    "",
    auth=_auth,
    response={201: list[QualityControlOperationResponse], 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_qc_operations(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    data: list[QualityControlOperationPostBody],
):
    """Append one or more operations to an in-progress session."""

    raise NotImplementedError


@qc_operation_router.get(
    "/{operation_id}",
    auth=_auth,
    response={200: QualityControlOperationResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_qc_operation(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    operation_id: Path[uuid.UUID],
):
    """Get a single QC operation by ID."""

    raise NotImplementedError


@qc_operation_router.patch(
    "/{operation_id}",
    auth=_auth,
    response={200: QualityControlOperationResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_qc_operation(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    operation_id: Path[uuid.UUID],
    data: QualityControlOperationPatchBody,
):
    """Update the comment or arguments of an operation in an in-progress session."""

    raise NotImplementedError


@qc_operation_router.delete(
    "/{operation_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_qc_operation(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    operation_id: Path[uuid.UUID],
):
    """Delete an operation from an in-progress session."""

    raise NotImplementedError