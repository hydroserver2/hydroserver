import uuid
from typing import Optional

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth
from processing.quality.services.session import QCSessionService
from interfaces.api.schemas.quality.session import (
    QualityControlSessionSummaryResponse,
    QualityControlSessionDetailResponse,
    QualityControlSessionQueryParameters,
    QualityControlSessionPostBody,
    QualityControlSessionPatchBody,
)

_auth = [session_auth, bearer_auth]

qc_session_router = Router(tags=["Quality Control Sessions"])
qc_session_service = QCSessionService()


@qc_session_router.get(
    "",
    auth=_auth,
    response={
        200: list[QualityControlSessionSummaryResponse] | list[QualityControlSessionDetailResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_qc_sessions(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    history_id: Path[uuid.UUID],
    query: Query[QualityControlSessionQueryParameters],
):
    """Get sessions for a QC history. Supports range_start/range_end overlap filtering, ancestor_of, and include_ancestors."""

    with raise_http_errors():
        count, sessions = qc_session_service.get_collection(
            history=history_id,
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
        return 200, [QualityControlSessionDetailResponse.model_validate(session) for session in sessions]

    return 200, [QualityControlSessionSummaryResponse.model_validate(session) for session in sessions]


@qc_session_router.post(
    "",
    auth=_auth,
    response={201: QualityControlSessionDetailResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    data: QualityControlSessionPostBody,
):
    """Create a new in-progress session for a QC history."""

    with raise_http_errors():
        session = qc_session_service.create(
            principal=request.principal,
            history=history_id,
            **data.model_dump(exclude_unset=True),
        )

    return 201, session


@qc_session_router.get(
    "/{session_id}",
    auth=_auth,
    response={
        200: QualityControlSessionSummaryResponse | QualityControlSessionDetailResponse,
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
    expand_related: Optional[bool] = None,
):
    """Get a QC session by ID. Includes dependencies and operations when expand_related=True."""

    with raise_http_errors():
        session = qc_session_service.get(
            history=history_id, session=session_id, principal=request.principal, expand_related=expand_related
        )

    if expand_related:
        return 200, QualityControlSessionDetailResponse.model_validate(session)

    return 200, QualityControlSessionSummaryResponse.model_validate(session)


@qc_session_router.patch(
    "/{session_id}",
    auth=_auth,
    response={200: QualityControlSessionDetailResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
    data: QualityControlSessionPatchBody,
):
    """Update an in-progress session's description."""

    with raise_http_errors():
        session = qc_session_service.update(
            history=history_id,
            session=session_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True),
        )

    return 200, session


@qc_session_router.delete(
    "/{session_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
):
    """Delete an in-progress session."""

    with raise_http_errors():
        qc_session_service.delete(
            history=history_id, session=session_id, principal=request.principal
        )

    return 204, None


@qc_session_router.post(
    "/{session_id}/commit",
    auth=_auth,
    response={200: QualityControlSessionDetailResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def commit_qc_session(
    request: HydroServerHttpRequest,
    history_id: Path[uuid.UUID],
    session_id: Path[uuid.UUID],
):
    """Commit an in-progress session after observations have been pushed to the managed datastream."""

    with raise_http_errors():
        session = qc_session_service.commit(
            history=history_id, session=session_id, principal=request.principal
        )

    return 200, session
