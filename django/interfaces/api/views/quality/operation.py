import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.quality.services.operation import QCOperationService, OperationInput
from interfaces.api.schemas.quality.operation import (
    QualityControlOperationResponse,
    QualityControlOperationQueryParameters,
    QualityControlOperationPostBody,
    QualityControlOperationPatchBody,
)

_auth = [session_auth, bearer_auth, apikey_auth]

qc_operation_router = Router(tags=["Quality Control Operations"])
qc_operation_service = QCOperationService()


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

    with raise_http_errors():
        count, operations = qc_operation_service.get_collection(
            history=history_id,
            session=session_id,
            principal=request.principal,
            **query.model_dump(exclude_unset=True),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, operations


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

    with raise_http_errors():
        operations = qc_operation_service.create(
            principal=request.principal,
            history=history_id,
            session=session_id,
            operations=[OperationInput(**item.model_dump()) for item in data],
        )

    return 201, operations


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

    with raise_http_errors():
        operation = qc_operation_service.get(
            history=history_id,
            session=session_id,
            operation=operation_id,
            principal=request.principal,
        )

    return 200, operation


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

    with raise_http_errors():
        operation = qc_operation_service.update(
            history=history_id,
            session=session_id,
            operation=operation_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True),
        )

    return 200, operation


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

    with raise_http_errors():
        qc_operation_service.delete(
            history=history_id,
            session=session_id,
            operation=operation_id,
            principal=request.principal,
        )

    return 204, None