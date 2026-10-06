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
    ExtentQueryParameters,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
    split_sortby,
    sortby_array_schema,
)
from interfaces.api.schemas.base import ItemId, NewItemId


class ResultQualifierFields(Schema):
    name: str = Field(..., max_length=255)
    description: str | None = None


RESULT_QUALIFIER_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ResultQualifierIncludeRelation = Literal[*RESULT_QUALIFIER_INCLUDE_RELATIONS.keys()]

_sortby_fields = ("name",)
ResultQualifierSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    *(to_camel(name) for name in ResultQualifierFields.model_fields),
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


class ResultQualifierItemQueryParameters(
    ResultQualifierFilterFields, BaseQueryParameters
):
    pass


class ResultQualifierQueryParameters(
    ResultQualifierFilterFields, CollectionQueryParameters, ExtentQueryParameters
):
    sortby: Annotated[
        Optional[list[ResultQualifierSortByFields]],
        BeforeValidator(split_sortby),
        WithJsonSchema(sortby_array_schema(ResultQualifierSortByFields)),
    ] = Query([], description="Select one or more fields to sort the response by.")
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter terms by workspace ID."
    )


class ResultQualifierResponse(BaseGetResponse, ResultQualifierFields, ItemId):
    workspace_id: Optional[uuid.UUID]


class ResultQualifierPostBody(BasePostBody, ResultQualifierFields, NewItemId):
    workspace_id: Optional[uuid.UUID] = None


class ResultQualifierPatchBody(BasePatchBody, ResultQualifierFields):
    pass
