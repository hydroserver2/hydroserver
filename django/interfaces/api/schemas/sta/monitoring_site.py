import uuid

from decimal import Decimal
from country_list import countries_for_language
from typing import Literal, Optional, Annotated
from ninja import Field, Query, Schema
from pydantic import BeforeValidator, WithJsonSchema, field_validator
from pydantic.alias_generators import to_camel

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePatchBody,
    BasePostBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.sta.linked_resource import LinkedResourceGetResponse
from interfaces.api.schemas.sta.tags import reject_empty_tag_keys_and_values


valid_country_codes = [code for code, _ in countries_for_language("en")]


class MonitoringSiteFields(Schema):
    name: str = Field(..., max_length=200)
    description: str
    code: str = Field(..., max_length=200)
    type: str = Field(..., max_length=200)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    # Preserve the established snake_case wire name used by both clients.
    elevation_m: Optional[float] = Field(
        None, ge=-99999, le=99999, alias="elevation_m"
    )
    elevation_datum: Optional[str] = Field(None, max_length=255)
    admin_area_1: Optional[str] = Field(None, max_length=200)
    admin_area_2: Optional[str] = Field(None, max_length=200)
    country: Optional[str] = Field(None, max_length=2)
    data_disclaimer: Optional[str] = None
    is_private: bool

    @field_validator("country", mode="after")
    def check_country_code(cls, value):
        if value and value.upper() not in valid_country_codes:
            raise ValueError(
                f"Invalid country code: {value}. Must be an ISO 3166-1 alpha-2 country code."
            )
        return value


MONITORING_SITE_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
MonitoringSiteIncludeRelation = Literal[*MONITORING_SITE_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "name",
    "code",
    "type",
    "isPrivate",
    "latitude",
    "longitude",
    "elevation_m",
    "elevationDatum",
    "adminArea1",
    "adminArea2",
    "country",
)
MonitoringSiteSortByFields = Literal[
    *_sortby_fields, *[f"-{field}" for field in _sortby_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    *(
        "elevation_m" if name == "elevation_m" else to_camel(name)
        for name in MonitoringSiteFields.model_fields
    ),
    "tags",
    "linkedResources",
)
MonitoringSitePropertyName = Literal[*_property_fields]


class MonitoringSiteFilterFields(Schema):
    properties: Annotated[
        Optional[list[MonitoringSitePropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringSitePropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[MonitoringSiteIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringSiteIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class MonitoringSiteItemQueryParameters(MonitoringSiteFilterFields, BaseQueryParameters):
    pass


class MonitoringSiteQueryParameters(MonitoringSiteFilterFields, CollectionQueryParameters):
    sortby: Optional[list[MonitoringSiteSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter monitoring sites by workspace ID."
    )
    bbox: list[str] = Query(
        [],
        description="Filter monitoring sites by bounding box. Format bounding box as {min_lon},{min_lat},{max_lon},{max_lat}",
    )
    admin_area_1: list[str] = Query(
        [], description="Filter monitoring sites by admin area 1."
    )
    admin_area_2: list[str] = Query(
        [], description="Filter monitoring sites by admin area 2."
    )
    country: list[str] = Query([], description="Filter monitoring sites by country.")
    type: list[str] = Query([], description="Filter monitoring sites by type.")
    tag: list[str] = Query(
        [], description="Filter monitoring sites by tag. Format tag filters as {key}:{value}"
    )
    is_private: Optional[bool] = Query(
        None,
        description="Controls whether the returned monitoring sites should be private or public.",
    )


class MonitoringSiteMarkerQueryParameters(BaseQueryParameters):
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter markers by workspace ID."
    )
    bbox: list[str] = Query(
        [],
        description="Filter markers by bounding box. Format bounding box as {min_lon},{min_lat},{max_lon},{max_lat}",
    )
    type: list[str] = Query([], description="Filter markers by monitoring site type.")


class MonitoringSiteMarkerResponse(BaseGetResponse):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str = Field(..., max_length=200)
    type: str = Field(..., max_length=200)
    is_private: bool
    latitude: float
    longitude: float


class SiteTypeIconResponse(BaseGetResponse):
    icon: str
    site_types: list[str]


class MonitoringSiteMapSummaryQueryParameters(BaseQueryParameters):
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter site summaries by workspace ID."
    )
    type: list[str] = Query([], description="Filter summaries by monitoring site type.")


class MonitoringSiteTaskSummaryQueryParameters(BaseQueryParameters):
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter task summaries by workspace ID."
    )
    type: list[str] = Query([], description="Filter summaries by monitoring site type.")


class MonitoringSiteTaskSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    type: str
    product_task_count: int = 0
    product_task_attention_count: int = 0
    monitoring_task_count: int = 0
    monitoring_task_attention_count: int = 0


class MonitoringSiteMapSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=200)
    type: str = Field(..., max_length=200)
    is_private: bool
    latitude: float
    longitude: float
    tags: dict[str, str]


class MonitoringSiteResponse(BaseGetResponse, MonitoringSiteFields):
    id: uuid.UUID
    workspace_id: uuid.UUID
    tags: dict[str, str] = {}
    monitoring_site_linked_resources: list[LinkedResourceGetResponse] = Field(..., alias="linkedResources")


class MonitoringSitePostBody(BasePostBody, MonitoringSiteFields):
    id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    tags: dict[str, str] = {}
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)
    elevation_m: Optional[Decimal] = Field(None, ge=-99999, le=99999, alias="elevation_m")

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)


class MonitoringSitePatchBody(BasePatchBody, MonitoringSiteFields):
    tags: dict[str, str | None] = {}
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)
    elevation_m: Optional[Decimal] = Field(None, ge=-99999, le=99999, alias="elevation_m")

    _validate_tags = field_validator("tags", mode="after")(reject_empty_tag_keys_and_values)
