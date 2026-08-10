import uuid
from typing import Literal, Optional, TYPE_CHECKING

from country_list import countries_for_language
from ninja import Field, Query, Schema
from pydantic import field_validator

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePatchBody,
    BasePostBody,
    BaseQueryParameters,
    CollectionQueryParameters,
)
from interfaces.api.schemas.sta.attachment import (
    FileAttachmentGetResponse,
    TagGetResponse,
    TagPostBody,
    tags_dict_to_list,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse


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


_order_by_fields = (
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

MonitoringSiteOrderByFields = Literal[
    *_order_by_fields, *[f"-{field}" for field in _order_by_fields]
]


class MonitoringSiteQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[MonitoringSiteOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
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
    tags: list[TagGetResponse]


class MonitoringSiteSummaryResponse(BaseGetResponse, MonitoringSiteFields):
    id: uuid.UUID
    workspace_id: uuid.UUID
    tags: list[TagGetResponse] = []
    monitoring_site_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )

    @field_validator("tags", mode="before")
    @classmethod
    def _tags_dict_to_list(cls, value):
        return tags_dict_to_list(value)


class MonitoringSiteDetailResponse(BaseGetResponse, MonitoringSiteFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse"
    tags: list[TagGetResponse] = []
    monitoring_site_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )

    @field_validator("tags", mode="before")
    @classmethod
    def _tags_dict_to_list(cls, value):
        return tags_dict_to_list(value)


class MonitoringSitePostBody(BasePostBody, MonitoringSiteFields):
    id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    tags: list[TagPostBody] = []


class MonitoringSitePatchBody(BasePatchBody, MonitoringSiteFields):
    pass
