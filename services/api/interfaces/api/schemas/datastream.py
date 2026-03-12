import uuid
from pydantic import AliasPath, AliasChoices
from ninja import Schema, Field, Query
from typing import Optional, Literal, TYPE_CHECKING
from interfaces.api.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)
from .attachment import TagGetResponse, FileAttachmentGetResponse

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse
    from interfaces.api.schemas import (
        ThingSummaryResponse,
        ObservedPropertySummaryResponse,
        UnitSummaryResponse,
        SensorSummaryResponse,
        ProcessingLevelSummaryResponse,
    )


class DatastreamFields(Schema):
    name: str = Field(..., max_length=255)
    description: str
    observation_type: str = Field(..., max_length=255)
    sampled_medium: str = Field(..., max_length=255)
    no_data_value: float
    aggregation_statistic: str = Field(..., max_length=255)
    time_aggregation_interval: float
    status: Optional[str] = Field(None, max_length=255)
    result_type: str = Field(..., max_length=255)
    value_count: Optional[int] = Field(None, ge=0)
    phenomenon_begin_time: Optional[ISODatetime] = None
    phenomenon_end_time: Optional[ISODatetime] = None
    result_begin_time: Optional[ISODatetime] = None
    result_end_time: Optional[ISODatetime] = None
    is_private: bool = False
    is_visible: bool = True
    time_aggregation_interval_unit: Literal["seconds", "minutes", "hours", "days"]
    intended_time_spacing: Optional[float] = None
    intended_time_spacing_unit: Optional[
        Literal["seconds", "minutes", "hours", "days"]
    ] = None


class DatastreamRelatedFields(Schema):
    thing_id: uuid.UUID
    sensor_id: uuid.UUID
    observed_property_id: uuid.UUID
    processing_level_id: uuid.UUID
    unit_id: uuid.UUID


_order_by_fields = (
    "name",
    "observationType",
    "sampledMedium",
    "status",
    "resultType",
    "isPrivate",
    "valueCount",
    "phenomenonBeginTime",
    "phenomenonEndTime",
    "resultBeginTime",
    "resultEndTime",
)

DatastreamOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class DatastreamQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[DatastreamOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing__workspace_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by workspace ID.", alias="workspace_id"
    )
    thing_id: list[uuid.UUID] = Query([], description="Filter datastreams by thing ID.")
    sensor_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by sensor ID."
    )
    observed_property_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by observed property ID."
    )
    processing_level_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by processing level ID."
    )
    unit_id: list[uuid.UUID] = Query([], description="Filter datastreams by unit ID.")
    observations__result_qualifier_id: list[uuid.UUID] = Query(
        [],
        description="Filter datastreams by observation result qualifier ID.",
        alias="result_qualifier_id",
    )
    observation_type: list[str] = Query(
        [], description="Filter things by observation type."
    )
    sampled_medium: list[str] = Query(
        [], description="Filter things by sampled medium."
    )
    status: list[str] = Query([], description="Filter things by status.")
    result_type: list[str] = Query([], description="Filter things by result type.")
    tag: list[str] = Query(
        [], description="Filter datastreams by tag. Format tag filters as {key}:{value}"
    )
    is_private: Optional[bool] = Query(
        None,
        description="Controls whether the datastreams should be private or public.",
    )
    value_count__lte: Optional[int] = Query(
        None,
        description="Sets the maximum value count of filtered datastreams.",
        alias="value_count_max",
    )
    value_count__gte: Optional[int] = Query(
        None,
        description="Sets the minimum value count of filtered datastreams.",
        alias="value_count_min",
    )
    phenomenon_begin_time__lte: Optional[ISODatetime] = Query(
        None,
        description="Sets the maximum phenomenon begin time of filtered datastreams.",
        alias="phenomenon_begin_time_max",
    )
    phenomenon_begin_time__gte: Optional[ISODatetime] = Query(
        None,
        description="Sets the minimum phenomenon begin time of filtered datastreams.",
        alias="phenomenon_begin_time_min",
    )
    phenomenon_end_time__lte: Optional[ISODatetime] = Query(
        None,
        description="Sets the maximum phenomenon end time of filtered datastreams.",
        alias="phenomenon_end_time_max",
    )
    phenomenon_end_time__gte: Optional[ISODatetime] = Query(
        None,
        description="Sets the minimum phenomenon end time of filtered datastreams.",
        alias="phenomenon_end_time_min",
    )
    result_begin_time__lte: Optional[ISODatetime] = Query(
        None,
        description="Sets the maximum result begin time of filtered datastreams.",
        alias="result_begin_time_max",
    )
    result_begin_time__gte: Optional[ISODatetime] = Query(
        None,
        description="Sets the minimum result begin time of filtered datastreams.",
        alias="result_begin_time_min",
    )
    result_end_time__lte: Optional[ISODatetime] = Query(
        None,
        description="Sets the maximum result end time of filtered datastreams.",
        alias="result_end_time_max",
    )
    result_end_time__gte: Optional[ISODatetime] = Query(
        None,
        description="Sets the minimum result end time of filtered datastreams.",
        alias="result_end_time_min",
    )


class DatastreamSummaryResponse(
    BaseGetResponse, DatastreamFields, DatastreamRelatedFields
):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("thing", "workspace_id"))
    )
    datastream_tags: list[TagGetResponse] = Field(..., alias="tags")
    datastream_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class DatastreamDetailResponse(BaseGetResponse, DatastreamFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse" = Field(
        ..., validation_alias=AliasPath("thing", "workspace")
    )
    thing: "ThingSummaryResponse"
    sensor: "SensorSummaryResponse"
    observed_property: "ObservedPropertySummaryResponse"
    processing_level: "ProcessingLevelSummaryResponse"
    unit: "UnitSummaryResponse"
    datastream_tags: list[TagGetResponse] = Field(..., alias="tags")
    datastream_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class DatastreamPostBody(BasePostBody, DatastreamFields, DatastreamRelatedFields):
    id: Optional[uuid.UUID] = None


class DatastreamPatchBody(BasePatchBody, DatastreamFields, DatastreamRelatedFields):
    pass
