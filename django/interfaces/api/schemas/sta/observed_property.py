import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from core.sta.models import ObservedPropertyType
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    ExtentQueryParameters,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
    split_sortby,
    sortby_array_schema,
)
from interfaces.api.schemas.sta.vocabulary import VocabularyResponse
from interfaces.api.schemas.base import ItemId, NewItemId


class ObservedPropertyFields(Schema):
    name: str = Field(..., max_length=255)
    definition: Optional[str] = Field(None, max_length=2000)
    description: str
    type: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=255)


OBSERVED_PROPERTY_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
    "type": {
        "bucket": "observedPropertyTypes",
        "response_schema": VocabularyResponse,
        "vocabulary_model": ObservedPropertyType,
        "value_field": "type",
    },
}
ObservedPropertyIncludeRelation = Literal[*OBSERVED_PROPERTY_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "name",
    "type",
    "code",
)
ObservedPropertySortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id", "workspaceId", *(to_camel(name) for name in ObservedPropertyFields.model_fields)
)
ObservedPropertyPropertyName = Literal[*_property_fields]


class ObservedPropertyFilterFields(Schema):
    properties: Annotated[
        Optional[list[ObservedPropertyPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ObservedPropertyPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ObservedPropertyIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ObservedPropertyIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ObservedPropertyItemQueryParameters(ObservedPropertyFilterFields, BaseQueryParameters):
    pass


class ObservedPropertyQueryParameters(ObservedPropertyFilterFields, CollectionQueryParameters, ExtentQueryParameters):
    sortby: Annotated[
        Optional[list[ObservedPropertySortByFields]],
        BeforeValidator(split_sortby),
        WithJsonSchema(sortby_array_schema(ObservedPropertySortByFields)),
    ] = Query([], description="Select one or more fields to sort the response by.")
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by monitoring_site ID.", alias="monitoringSiteId"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter observed properties by datastream ID.",
        alias="datastreamId",
    )
    type: list[str] = Query([], description="Filter observed properties by type")


class ObservedPropertyResponse(BaseGetResponse, ObservedPropertyFields, ItemId):
    workspace_id: Optional[uuid.UUID] = None


class ObservedPropertyPostBody(BasePostBody, ObservedPropertyFields, NewItemId):
    workspace_id: Optional[uuid.UUID]


class ObservedPropertyPatchBody(BasePatchBody, ObservedPropertyFields):
    pass
