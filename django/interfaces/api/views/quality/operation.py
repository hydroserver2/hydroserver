import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.quality.operation import QCOperationAPIService, OperationInput
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.quality.operation import (
    QualityControlOperationResponse,
    QualityControlOperationQueryParameters,
    QualityControlOperationItemQueryParameters,
    QualityControlOperationPostBody,
    QualityControlOperationPatchBody,
)

qc_operation_router = Router(tags=["Quality Control Operations"])
qc_operation_service = QCOperationAPIService()


@qc_operation_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={200: PaginatedResponse[QualityControlOperationResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_qc_operations(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    query: Query[QualityControlOperationQueryParameters],
):
    """Get all operations for a QC session in execution order."""

    return 200, qc_operation_service.list(
        principal=request.principal,
        history=history_id,
        session=session_id,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
    )


@qc_operation_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={201: list[CreatedResponse], 400: str, 401: str, 403: str, 404: str},
    by_alias=True,
)
def create_qc_operations(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    data: list[QualityControlOperationPostBody],
):
    """Append one or more operations to an in-progress session."""

    return 201, qc_operation_service.create(
        principal=request.principal,
        history=history_id,
        session=session_id,
        operations=[OperationInput(**item.model_dump()) for item in data],
    )


@qc_operation_router.get(
    "/{operation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={200: ItemResponse[QualityControlOperationResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_qc_operation(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    operation_id: Path[uuid.UUID],
    query: Query[QualityControlOperationItemQueryParameters],
):
    """Get a single QC operation by ID."""

    return 200, qc_operation_service.get_item(
        principal=request.principal,
        history=history_id,
        session=session_id,
        operation=operation_id,
    )


@qc_operation_router.patch(
    "/{operation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 400: str, 401: str, 403: str, 404: str},
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

    qc_operation_service.update(
        history=history_id,
        session=session_id,
        operation=operation_id,
        principal=request.principal,
        **data.dict(exclude_unset=True),
    )

    return 204, None


@qc_operation_router.delete(
    "/{operation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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

    qc_operation_service.delete(
        history=history_id,
        session=session_id,
        operation=operation_id,
        principal=request.principal,
    )

    return 204, None
