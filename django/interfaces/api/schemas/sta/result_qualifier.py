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


class ResultQualifierFields(Schema):
    code: str = Field(..., max_length=255)
    description: str


RESULT_QUALIFIER_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ResultQualifierIncludeRelation = Literal[*RESULT_QUALIFIER_INCLUDE_RELATIONS.keys()]

_sortby_fields = ("code",)
ResultQualifierSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id", "workspaceId", *(to_camel(name) for name in ResultQualifierFields.model_fields)
)
ResultQualifierPropertyName = Literal[*_property_fields]


class ResultQualifierFilterFields(Schema):
    properties: Annotated[
        Optional[list[ResultQualifierPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ResultQualifierPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ResultQualifierIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ResultQualifierIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ResultQualifierItemQueryParameters(ResultQualifierFilterFields, BaseQueryParameters):
    pass


class ResultQualifierQueryParameters(ResultQualifierFilterFields, CollectionQueryParameters):
    sortby: Optional[list[ResultQualifierSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter result qualifiers by workspace ID."
    )
    observations__datastream__monitoring_site_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter result qualifiers by monitoring_site ID.", alias="monitoring_site_id"
    )
    observations__datastream_id: list[uuid.UUID | Literal["null"]] = Query(
        [],
        description="Filter result qualifiers by datastream ID.",
        alias="datastream_id",
    )


class ResultQualifierResponse(BaseGetResponse, ResultQualifierFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class ResultQualifierPostBody(BasePostBody, ResultQualifierFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class ResultQualifierPatchBody(BasePatchBody, ResultQualifierFields):
    pass
