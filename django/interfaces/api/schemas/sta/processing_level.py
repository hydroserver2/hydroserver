import uuid
from typing import Optional, Literal, TYPE_CHECKING
from ninja import Schema, Field, Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse


class ProcessingLevelFields(Schema):
    code: str = Field(..., max_length=255)
    definition: Optional[str] = None
    explanation: Optional[str] = None


_order_by_fields = ("code",)

ProcessingLevelOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class ProcessingLevelQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[ProcessingLevelOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter processing levels by workspace ID."
    )
    datastreams__thing_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter processing levels by thing ID.", alias="thing_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter processing levels by datastream ID.",
        alias="datastream_id",
    )


class ProcessingLevelSummaryResponse(BaseGetResponse, ProcessingLevelFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class ProcessingLevelDetailResponse(BaseGetResponse, ProcessingLevelFields):
    id: uuid.UUID
    workspace: Optional["WorkspaceSummaryResponse"]


class ProcessingLevelPostBody(BasePostBody, ProcessingLevelFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class ProcessingLevelPatchBody(BasePatchBody, ProcessingLevelFields):
    pass
