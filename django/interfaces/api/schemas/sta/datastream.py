import uuid

from typing import Optional, Literal, Annotated
from pydantic import AliasPath, AliasChoices, BeforeValidator, WithJsonSchema, field_validator
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    WorkspaceResponse,
    MonitoringSiteResponse,
    ObservedPropertyResponse,
    UnitResponse,
    MethodResponse,
    ProcessingLevelResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.sta.linked_resource import LinkedResourceGetResponse
from interfaces.api.schemas.sta.tags import reject_empty_tag_keys_and_values
from interfaces.api.schemas.sta.vocabulary import VocabularyResponse
from core.sta.models import SampledMedium, AggregationStatistic, DatastreamStatus


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


DATASTREAM_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "monitoring_site__workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
    "monitoringSite": {
        "path": "monitoring_site",
        "bucket": "monitoringSites",
        "response_schema": MonitoringSiteResponse,
    },
    "method": {
        "path": "method",
        "bucket": "methods",
        "response_schema": MethodResponse,
    },
    "observedProperty": {
        "path": "observed_property",
        "bucket": "observedProperties",
        "response_schema": ObservedPropertyResponse,
    },
    "processingLevel": {
        "path": "processing_level",
        "bucket": "processingLevels",
        "response_schema": ProcessingLevelResponse,
    },
    "unit": {
        "path": "unit",
        "bucket": "units",
        "response_schema": UnitResponse,
    },
    "sampledMedium": {
        "bucket": "sampledMediums",
        "response_schema": VocabularyResponse,
        "vocabulary_model": SampledMedium,
        "value_field": "sampled_medium",
    },
    "aggregationStatistic": {
        "bucket": "aggregationStatistics",
        "response_schema": VocabularyResponse,
        "vocabulary_model": AggregationStatistic,
        "value_field": "aggregation_statistic",
    },
    "status": {
        "bucket": "datastreamStatuses",
        "response_schema": VocabularyResponse,
        "vocabulary_model": DatastreamStatus,
        "value_field": "status",
    },
}
DatastreamIncludeRelation = Literal[*DATASTREAM_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "name",
    "observationType",
    "sampledMedium",
    "status",
    "resultType",
    "isPrivate",
    "isVisible",
    "aggregationStatistic",
    "valueCount",
    "phenomenonBeginTime",
    "phenomenonEndTime",
    "resultBeginTime",
    "resultEndTime",
)
DatastreamSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    *(to_camel(name) for name in DatastreamFields.model_fields),
    *(to_camel(name) for name in DatastreamRelatedFields.model_fields),
    "tags",
    "linkedResources",
)
DatastreamPropertyName = Literal[*_property_fields]


class DatastreamFilterFields(Schema):
    properties: Annotated[
        Optional[list[DatastreamPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DatastreamPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[DatastreamIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DatastreamIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class DatastreamItemQueryParameters(DatastreamFilterFields, BaseQueryParameters):
    pass


class DatastreamQueryParameters(DatastreamFilterFields, CollectionQueryParameters):
    sortby: Optional[list[DatastreamSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
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
    method_id: uuid.UUID
    method_name: str = Field(..., max_length=255)
    observed_property_id: uuid.UUID
    processing_level_id: uuid.UUID
    unit_id: uuid.UUID
    unit_name: str = Field(..., max_length=255)
    unit_symbol: str = Field(..., max_length=255)
    no_data_value: float
    aggregation_statistic: str = Field(..., max_length=255)
    time_aggregation_interval: float
    time_aggregation_interval_unit: Literal[
        "seconds", "minutes", "hours", "days"
    ]
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


class DatastreamResponse(
    BaseGetResponse, DatastreamFields, DatastreamRelatedFields
):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("monitoring_site", "workspace_id"))
    )
    tags: dict[str, str] = {}
    datastream_linked_resources: list[LinkedResourceGetResponse] = Field(..., alias="linkedResources")


class DatastreamPostBody(BasePostBody, DatastreamFields, DatastreamRelatedFields):
    id: Optional[uuid.UUID] = None
    tags: dict[str, str] = {}

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)


class DatastreamPatchBody(BasePatchBody, DatastreamFields, DatastreamRelatedFields):
    tags: dict[str, str | None] = {}

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)
