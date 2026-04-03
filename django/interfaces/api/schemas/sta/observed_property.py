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


class ObservedPropertyFields(Schema):
    name: str = Field(..., max_length=255)
    definition: str
    description: str
    observed_property_type: str = Field(..., max_length=255, alias="type")
    code: str = Field(..., max_length=255)


_order_by_fields = (
    "name",
    "type",
    "code",
)

ObservedPropertyOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class ObservedPropertyQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[ObservedPropertyOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by workspace ID."
    )
    datastreams__thing_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by thing ID.", alias="thing_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter observed properties by datastream ID.",
        alias="datastream_id",
    )
    observed_property_type: list[str] = Query(
        [], description="Filter observed properties by type", alias="type"
    )


class ObservedPropertySummaryResponse(BaseGetResponse, ObservedPropertyFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None


class ObservedPropertyDetailResponse(BaseGetResponse, ObservedPropertyFields):
    id: uuid.UUID
    workspace: Optional["WorkspaceSummaryResponse"]


class ObservedPropertyPostBody(BasePostBody, ObservedPropertyFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID]


class ObservedPropertyPatchBody(BasePatchBody, ObservedPropertyFields):
    pass
