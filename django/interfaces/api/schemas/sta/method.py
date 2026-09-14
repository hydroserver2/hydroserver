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


class MethodFields(Schema):
    name: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: str = Field(..., max_length=100)
    description: str
    definition: Optional[str] = Field(None, max_length=500)
    sensor_model: Optional[str] = Field(None, max_length=255)
    sensor_model_manufacturer: Optional[str] = Field(None, max_length=255)
    sensor_model_definition: Optional[str] = Field(None, max_length=500)


METHOD_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
MethodIncludeRelation = Literal[*METHOD_INCLUDE_RELATIONS.keys()]

_order_by_fields = (
    "name",
    "code",
    "type",
    "sensorModel",
    "sensorModelManufacturer",
)
MethodOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]

_property_fields = ("id", "workspaceId", *(to_camel(name) for name in MethodFields.model_fields))
MethodPropertyName = Literal[*_property_fields]


class MethodFilterFields(Schema):
    properties: Annotated[
        Optional[list[MethodPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MethodPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[MethodIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MethodIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class MethodItemQueryParameters(MethodFilterFields, BaseQueryParameters):
    pass


class MethodQueryParameters(MethodFilterFields, CollectionQueryParameters):
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


class MethodResponse(BaseGetResponse, MethodFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class MethodPostBody(BasePostBody, MethodFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class MethodPatchBody(BasePatchBody, MethodFields):
    pass
