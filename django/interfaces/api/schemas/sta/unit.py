import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from core.sta.models import UnitType
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


class UnitFields(Schema):
    name: str = Field(..., max_length=255)
    symbol: str = Field(..., max_length=255)
    definition: Optional[str] = Field(None, max_length=2000)
    type: str = Field(..., max_length=255)


UNIT_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
    "type": {
        "bucket": "unitTypes",
        "response_schema": VocabularyResponse,
        "vocabulary_model": UnitType,
        "value_field": "type",
    },
}
UnitIncludeRelation = Literal[*UNIT_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "name",
    "symbol",
    "type",
)
UnitSortByFields = Literal[*_sortby_fields, *[f"-{f}" for f in _sortby_fields]]

_property_fields = ("id", "workspaceId", *(to_camel(name) for name in UnitFields.model_fields))
UnitPropertyName = Literal[*_property_fields]


class UnitFilterFields(Schema):
    properties: Annotated[
        Optional[list[UnitPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(UnitPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[UnitIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(UnitIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class UnitItemQueryParameters(UnitFilterFields, BaseQueryParameters):
    pass


class UnitQueryParameters(UnitFilterFields, CollectionQueryParameters, ExtentQueryParameters):
    sortby: Annotated[
        Optional[list[UnitSortByFields]],
        BeforeValidator(split_sortby),
        WithJsonSchema(sortby_array_schema(UnitSortByFields)),
    ] = Query([], description="Select one or more fields to sort the response by.")
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by monitoring_site ID.", alias="monitoringSiteId"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by datastream ID.", alias="datastreamId"
    )
    type: list[str] = Query([], description="Filter units by type")


class UnitResponse(BaseGetResponse, UnitFields, ItemId):
    workspace_id: Optional[uuid.UUID]


class UnitPostBody(BasePostBody, UnitFields, NewItemId):
    workspace_id: Optional[uuid.UUID] = None


class UnitPatchBody(BasePatchBody, UnitFields):
    pass
