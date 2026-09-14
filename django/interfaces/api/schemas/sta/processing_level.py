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


class ProcessingLevelFields(Schema):
    code: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: str
    definition: Optional[str] = None


PROCESSING_LEVEL_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ProcessingLevelIncludeRelation = Literal[*PROCESSING_LEVEL_INCLUDE_RELATIONS.keys()]

_order_by_fields = ("code", "name")
ProcessingLevelOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id", "workspaceId", *(to_camel(name) for name in ProcessingLevelFields.model_fields)
)
ProcessingLevelPropertyName = Literal[*_property_fields]


class ProcessingLevelFilterFields(Schema):
    properties: Annotated[
        Optional[list[ProcessingLevelPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ProcessingLevelPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ProcessingLevelIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ProcessingLevelIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ProcessingLevelItemQueryParameters(ProcessingLevelFilterFields, BaseQueryParameters):
    pass


class ProcessingLevelQueryParameters(ProcessingLevelFilterFields, CollectionQueryParameters):
    order_by: Optional[list[ProcessingLevelOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter processing levels by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter processing levels by monitoring_site ID.", alias="monitoring_site_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter processing levels by datastream ID.",
        alias="datastream_id",
    )


class ProcessingLevelResponse(BaseGetResponse, ProcessingLevelFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class ProcessingLevelPostBody(BasePostBody, ProcessingLevelFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class ProcessingLevelPatchBody(BasePatchBody, ProcessingLevelFields):
    pass
