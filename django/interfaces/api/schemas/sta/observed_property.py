import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
)


class ObservedPropertyFields(Schema):
    name: str = Field(..., max_length=255)
    definition: Optional[str] = None
    description: str
    type: str = Field(..., max_length=500)
    code: str = Field(..., max_length=500)


OBSERVED_PROPERTY_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ObservedPropertyIncludeRelation = Literal[*OBSERVED_PROPERTY_INCLUDE_RELATIONS.keys()]

_order_by_fields = (
    "name",
    "type",
    "code",
)
ObservedPropertyOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
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


class ObservedPropertyQueryParameters(ObservedPropertyFilterFields, CollectionQueryParameters):
    order_by: Optional[list[ObservedPropertyOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter observed properties by monitoring_site ID.", alias="monitoring_site_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter observed properties by datastream ID.",
        alias="datastream_id",
    )
    type: list[str] = Query([], description="Filter observed properties by type")


class ObservedPropertyResponse(BaseGetResponse, ObservedPropertyFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None


class ObservedPropertyPostBody(BasePostBody, ObservedPropertyFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID]


class ObservedPropertyPatchBody(BasePatchBody, ObservedPropertyFields):
    pass
