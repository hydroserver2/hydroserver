import uuid
from typing import Optional, Literal, TYPE_CHECKING
from ninja import Schema, Field, Query
from pydantic import field_validator, AliasChoices
from country_list import countries_for_language
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)
from .attachment import TagGetResponse, FileAttachmentGetResponse

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse

valid_country_codes = [code for code, _ in countries_for_language("en")]


class LocationFields(Schema):
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        validation_alias=AliasChoices("latitude", "location.latitude"),
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        validation_alias=AliasChoices("longitude", "location.longitude"),
    )
    elevation_m: Optional[float] = Field(
        None,
        ge=-99999,
        le=99999,
        alias="elevation_m",
        validation_alias=AliasChoices("elevation_m", "location.elevation_m"),
    )
    elevation_datum: Optional[str] = Field(
        None,
        max_length=255,
        validation_alias=AliasChoices("elevationDatum", "location.elevation_datum"),
    )
    admin_area_1: Optional[str] = Field(
        None, max_length=200, validation_alias=AliasChoices("adminArea1", "location.admin_area_1")
    )
    admin_area_2: Optional[str] = Field(
        None, max_length=200, validation_alias=AliasChoices("adminArea2", "location.admin_area_2")
    )
    country: Optional[str] = Field(
        None, max_length=2, validation_alias=AliasChoices("country", "location.country")
    )

    @field_validator("country", mode="after")
    def check_country_code(cls, value):
        if value and value.upper() not in valid_country_codes:
            raise ValueError(
                f"Invalid country code: {value}. Must be an ISO 3166-1 alpha-2 country code."
            )
        return value


class LocationDetailResponse(BaseGetResponse, LocationFields):
    pass


class LocationPostBody(BasePostBody, LocationFields):
    pass


class LocationPatchBody(BasePatchBody, LocationFields):
    pass


class ThingFields(Schema):
    name: str = Field(..., max_length=200)
    description: str
    sampling_feature_type: str = Field(..., max_length=200)
    sampling_feature_code: str = Field(..., max_length=200)
    site_type: str = Field(..., max_length=200)
    data_disclaimer: Optional[str] = None
    is_private: bool


_order_by_fields = (
    "name",
    "samplingFeatureType",
    "samplingFeatureCode",
    "siteType",
    "isPrivate",
    "latitude",
    "longitude",
    "elevation_m",
    "elevationDatum",
    "adminArea1",
    "adminArea2",
    "country",
)

ThingOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]


class ThingQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[ThingOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter things by workspace ID."
    )
    bbox: list[str] = Query(
        [],
        description="Filter things by bounding box. Format bounding box as {min_lon},{min_lat},{max_lon},{max_lat}",
    )
    locations__admin_area_1: list[str] = Query(
        [], description="Filter things by admin area 1.", alias="adminArea1"
    )
    locations__admin_area_2: list[str] = Query(
        [], description="Filter things by admin area 2.", alias="adminArea2"
    )
    locations__country: list[str] = Query(
        [], description="Filter things by country.", alias="country"
    )
    site_type: list[str] = Query([], description="Filter things by site type.")
    sampling_feature_type: list[str] = Query(
        [], description="Filter things by sampling feature type."
    )
    tag: list[str] = Query(
        [], description="Filter things by tag. Format tag filters as {key}:{value}"
    )
    is_private: Optional[bool] = Query(
        None,
        description="Controls whether the returned things should be private or public.",
    )


class ThingSummaryResponse(BaseGetResponse, ThingFields):
    id: uuid.UUID
    workspace_id: uuid.UUID
    location: LocationDetailResponse
    thing_tags: list[TagGetResponse] = Field(..., alias="tags")
    thing_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class ThingDetailResponse(BaseGetResponse, ThingFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse"
    location: LocationDetailResponse
    thing_tags: list[TagGetResponse] = Field(..., alias="tags")
    thing_file_attachments: list[FileAttachmentGetResponse] = Field(
        ..., alias="fileAttachments"
    )


class ThingPostBody(BasePostBody, ThingFields):
    id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    location: LocationPostBody


class ThingPatchBody(BasePatchBody, ThingFields):
    location: Optional[LocationPatchBody] = None
