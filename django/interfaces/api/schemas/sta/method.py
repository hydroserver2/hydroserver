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


class MethodFields(Schema):
    name: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: str = Field(..., max_length=100)
    description: str
    definition: Optional[str] = Field(None, max_length=500)
    sensor_model: Optional[str] = Field(None, max_length=255)
    sensor_model_manufacturer: Optional[str] = Field(None, max_length=255)
    sensor_model_definition: Optional[str] = Field(None, max_length=500)


_order_by_fields = (
    "name",
    "code",
    "type",
    "sensorModel",
    "sensorModelManufacturer",
)

MethodOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]


class MethodQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[MethodOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter methods by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter methods by monitoring_site ID.", alias="monitoring_site_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter methods by datastream ID.", alias="datastream_id"
    )
    type: list[str] = Query([], description="Filter methods by type")
    sensor_model: list[str] = Query([], description="Filter methods by sensor model")
    sensor_model_manufacturer: list[str] = Query(
        [], description="Filter methods by sensor model manufacturer"
    )


class MethodSummaryResponse(BaseGetResponse, MethodFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class MethodDetailResponse(BaseGetResponse, MethodFields):
    id: uuid.UUID
    workspace: Optional["WorkspaceSummaryResponse"]


class MethodPostBody(BasePostBody, MethodFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class MethodPatchBody(BasePatchBody, MethodFields):
    pass
