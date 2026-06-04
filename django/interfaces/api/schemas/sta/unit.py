import uuid
from ninja import Schema, Field, Query
from typing import Optional, Literal, TYPE_CHECKING
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse


class UnitFields(Schema):
    name: str = Field(..., max_length=255)
    symbol: str = Field(..., max_length=255)
    definition: str
    unit_type: str = Field(..., max_length=255, alias="type")


_order_by_fields = (
    "name",
    "symbol",
    "type",
)

UnitOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]


class UnitQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[UnitOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by workspace ID."
    )
    datastreams__thing_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by thing ID.", alias="thing_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by datastream ID.", alias="datastream_id"
    )
    unit_type: list[str] = Query([], description="Filter units by type", alias="type")


class UnitSummaryResponse(BaseGetResponse, UnitFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class UnitDetailResponse(BaseGetResponse, UnitFields):
    id: uuid.UUID
    workspace: Optional["WorkspaceSummaryResponse"]


class UnitPostBody(BasePostBody, UnitFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class UnitPatchBody(BasePatchBody, UnitFields):
    pass
