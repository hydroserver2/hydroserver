import uuid
from ninja import Query
from typing import Literal, Optional
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    AccountContactDetailResponse,
)
from interfaces.api.schemas.quality.operation import QualityControlOperationResponse

SessionStatus = Literal["in_progress", "committed"]


class QualityControlSessionSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    history_id: uuid.UUID
    created_by: AccountContactDetailResponse
    created_at: ISODatetime
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    status: SessionStatus
    committed_at: Optional[ISODatetime] = None
    description: Optional[str] = None
    source_checksum: str
    managed_checksum: Optional[str] = None


class QualityControlSessionDetailResponse(BaseGetResponse):
    id: uuid.UUID
    history_id: uuid.UUID
    created_by: AccountContactDetailResponse
    created_at: ISODatetime
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    status: SessionStatus
    committed_at: Optional[ISODatetime] = None
    description: Optional[str] = None
    source_checksum: str
    managed_checksum: Optional[str] = None
    dependency_ids: list[uuid.UUID]
    operations: list[QualityControlOperationResponse]


class QualityControlSessionQueryParameters(CollectionQueryParameters):
    status: Optional[SessionStatus] = None
    range_start: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range start.")
    range_end: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range end.")
    ancestor_of: Optional[uuid.UUID] = Query(None, description="Return all transitive ancestors of the given session ID.")
    include_ancestors: bool = Query(False, description="Also return transitive ancestors of all sessions matched by other filters.")


class QualityControlSessionPostBody(BasePostBody):
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    description: Optional[str] = None


class QualityControlSessionPatchBody(BasePatchBody):
    description: Optional[str] = None
