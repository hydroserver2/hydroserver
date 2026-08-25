import uuid
from pydantic import AliasPath, AliasChoices, field_validator
from ninja import Schema, Field, Query
from typing import Optional, Literal, TYPE_CHECKING
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
)
from interfaces.api.schemas.sta.attachment import FileAttachmentGetResponse
from interfaces.api.schemas.sta.tags import reject_empty_tag_keys_and_values

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse
    from interfaces.api.schemas import (
        MonitoringSiteSummaryResponse,
        ObservedPropertySummaryResponse,
        UnitSummaryResponse,
        MethodSummaryResponse,
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
    monitoring_site_id: uuid.UUID
    method_id: uuid.UUID
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
    monitoring_site__workspace_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by workspace ID.", alias="workspace_id"
    )
    monitoring_site_id: list[uuid.UUID] = Query([], description="Filter datastreams by monitoring_site ID.")
    method_id: list[uuid.UUID] = Query(
        [], description="Filter datastreams by method ID."
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
        [], description="Filter monitoring_sites by observation type."
    )
    sampled_medium: list[str] = Query(
        [], description="Filter monitoring_sites by sampled medium."
    )
    status: list[str] = Query([], description="Filter monitoring_sites by status.")
    result_type: list[str] = Query([], description="Filter monitoring_sites by result type.")
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


class DatastreamVisualizationBootstrapQueryParameters(BaseQueryParameters):
    monitoring_site__workspace_id: list[uuid.UUID] = Query(
        [], description="Filter visualization bootstrap datastreams by workspace ID.", alias="workspace_id"
    )


class VisualizationMonitoringSiteResponse(BaseGetResponse):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=200)


class VisualizationObservedPropertyResponse(BaseGetResponse):
    id: uuid.UUID
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=255)


class VisualizationProcessingLevelResponse(BaseGetResponse):
    id: uuid.UUID
    name: str = Field(..., max_length=255)


class VisualizationDatastreamResponse(BaseGetResponse):
    id: uuid.UUID
    name: str = Field(..., max_length=255)
    monitoring_site_id: uuid.UUID
    observed_property_id: uuid.UUID
    processing_level_id: uuid.UUID
    unit_id: uuid.UUID
    no_data_value: float
    value_count: Optional[int] = Field(None, ge=0)
    phenomenon_begin_time: Optional[ISODatetime] = None
    phenomenon_end_time: Optional[ISODatetime] = None
    intended_time_spacing: Optional[float] = None
    intended_time_spacing_unit: Optional[
        Literal["seconds", "minutes", "hours", "days"]
    ] = None


class DatastreamVisualizationBootstrapResponse(BaseGetResponse):
    monitoring_sites: list[VisualizationMonitoringSiteResponse]
    datastreams: list[VisualizationDatastreamResponse]
    observed_properties: list[VisualizationObservedPropertyResponse]
    processing_levels: list[VisualizationProcessingLevelResponse]


class DatastreamSummaryResponse(
    BaseGetResponse, DatastreamFields, DatastreamRelatedFields
):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("monitoring_site", "workspace_id"))
    )
    tags: dict[str, str] = {}
    datastream_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class DatastreamDetailResponse(BaseGetResponse, DatastreamFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse" = Field(
        ..., validation_alias=AliasPath("monitoring_site", "workspace")
    )
    monitoring_site: "MonitoringSiteSummaryResponse"
    method: "MethodSummaryResponse"
    observed_property: "ObservedPropertySummaryResponse"
    processing_level: "ProcessingLevelSummaryResponse"
    unit: "UnitSummaryResponse"
    tags: dict[str, str] = {}
    datastream_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class DatastreamPostBody(BasePostBody, DatastreamFields, DatastreamRelatedFields):
    id: Optional[uuid.UUID] = None
    tags: dict[str, str] = {}

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)


class DatastreamPatchBody(BasePatchBody, DatastreamFields, DatastreamRelatedFields):
    tags: dict[str, str | None] = {}

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)
