import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.quality.session import QCSessionAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.quality.session import (
    QualityControlSessionResponse,
    QualityControlSessionQueryParameters,
    QualityControlSessionItemQueryParameters,
    QualityControlSessionPostBody,
    QualityControlSessionPatchBody,
)

qc_session_router = Router(tags=["Quality Control Sessions"])
qc_session_service = QCSessionAPIService()


@qc_session_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[QualityControlSessionResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_qc_sessions(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    query: Query[QualityControlSessionQueryParameters],
):
    """Get sessions for a QC history. Supports range_start/range_end overlap filtering, ancestor_of, and include_ancestors."""

    return 200, qc_session_service.list(
        principal=request.principal,
        history=history_id,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
    )


@qc_session_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={201: CreatedResponse, 400: str, 401: str, 403: str, 404: str},
    by_alias=True,
)
def create_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    data: QualityControlSessionPostBody,
):
    """Create a new in-progress session for a QC history."""

    return 201, qc_session_service.create(
        principal=request.principal,
        history=history_id,
        **data.dict(exclude_unset=True),
    )


@qc_session_router.get(
    "/{session_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[QualityControlSessionResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    query: Query[QualityControlSessionItemQueryParameters],
):
    """Get a QC session by ID."""

    return 200, qc_session_service.get_item(
        principal=request.principal, history=history_id, session=session_id
    )


@qc_session_router.patch(
    "/{session_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 400: str, 401: str, 403: str, 404: str},
    by_alias=True,
)
def update_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    data: QualityControlSessionPatchBody,
):
    """Update an in-progress session's description."""

    qc_session_service.update(
        history=history_id,
        session=session_id,
        principal=request.principal,
        **data.dict(exclude_unset=True),
    )

    return 204, None


@qc_session_router.delete(
    "/{session_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
):
    """Delete an in-progress session."""

    qc_session_service.delete(
        history=history_id, session=session_id, principal=request.principal
    )

    return 204, None


@qc_session_router.post(
    "/{session_id}/commit",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={204: None, 400: str, 401: str, 403: str, 404: str},
    by_alias=True,
)
def commit_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
):
    """Commit an in-progress session after observations have been pushed to the managed datastream."""

    qc_session_service.commit(
        history=history_id, session=session_id, principal=request.principal
    )

    return 204, None
