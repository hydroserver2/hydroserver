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


class UnitFields(Schema):
    name: str = Field(..., max_length=255)
    symbol: str = Field(..., max_length=255)
    definition: Optional[str] = None
    type: str = Field(..., max_length=255)


UNIT_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
UnitIncludeRelation = Literal[*UNIT_INCLUDE_RELATIONS.keys()]

_order_by_fields = (
    "name",
    "symbol",
    "type",
)
UnitOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]

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


class UnitQueryParameters(UnitFilterFields, CollectionQueryParameters):
    order_by: Optional[list[UnitOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by workspace ID."
    )
    datastreams__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by monitoring_site ID.", alias="monitoring_site_id"
    )
    datastreams__id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter units by datastream ID.", alias="datastream_id"
    )
    type: list[str] = Query([], description="Filter units by type")


class UnitResponse(BaseGetResponse, UnitFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class UnitPostBody(BasePostBody, UnitFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class UnitPatchBody(BasePatchBody, UnitFields):
    pass
