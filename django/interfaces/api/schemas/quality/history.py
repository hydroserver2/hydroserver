import uuid
from typing import Optional, TYPE_CHECKING
from ninja import Query
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import DatastreamSummaryResponse


class QualityControlHistoryFields:
    description: Optional[str] = None


class QualityControlHistorySummaryResponse(BaseGetResponse):
    id: uuid.UUID
    managed_datastream_id: uuid.UUID
    source_datastream_id: uuid.UUID
    created_at: ISODatetime
    description: Optional[str] = None
    phenomenon_time_start: Optional[ISODatetime] = None
    phenomenon_time_end: Optional[ISODatetime] = None
    source_checksum: Optional[str] = None
    managed_checksum: Optional[str] = None


class QualityControlHistoryDetailResponse(BaseGetResponse):
    id: uuid.UUID
    managed_datastream: "DatastreamSummaryResponse"
    source_datastream: "DatastreamSummaryResponse"
    created_at: ISODatetime
    description: Optional[str] = None
    phenomenon_time_start: Optional[ISODatetime] = None
    phenomenon_time_end: Optional[ISODatetime] = None
    source_checksum: Optional[str] = None
    managed_checksum: Optional[str] = None


class QualityControlHistoryQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    managed_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter histories by managed datastream ID."
    )
    source_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter histories by source datastream ID."
    )


class QualityControlHistoryPostBody(BasePostBody):
    managed_datastream_id: uuid.UUID
    source_datastream_id: uuid.UUID
    description: Optional[str] = None


class QualityControlHistoryPatchBody(BasePatchBody):
    description: Optional[str] = None
