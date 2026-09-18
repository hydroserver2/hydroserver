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


class ControlledVocabularyFields(Schema):
    name: str = Field(..., max_length=255)
    description: str = ""
    is_active: bool = True


CONTROLLED_VOCABULARY_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ControlledVocabularyIncludeRelation = Literal[
    *CONTROLLED_VOCABULARY_INCLUDE_RELATIONS.keys()
]

_sortby_fields = ("name",)
ControlledVocabularySortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    *(to_camel(name) for name in ControlledVocabularyFields.model_fields),
)
ControlledVocabularyPropertyName = Literal[*_property_fields]


class ControlledVocabularyFilterFields(Schema):
    properties: Annotated[
        Optional[list[ControlledVocabularyPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ControlledVocabularyPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ControlledVocabularyIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ControlledVocabularyIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ControlledVocabularyItemQueryParameters(
    ControlledVocabularyFilterFields, BaseQueryParameters
):
    pass


class ControlledVocabularyQueryParameters(
    ControlledVocabularyFilterFields, CollectionQueryParameters
):
    sortby: Optional[list[ControlledVocabularySortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter terms by workspace ID."
    )
    is_active: Optional[bool] = Query(
        None, description="Filter terms by active status."
    )


class ControlledVocabularyResponse(BaseGetResponse, ControlledVocabularyFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]


class ControlledVocabularyPostBody(BasePostBody, ControlledVocabularyFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class ControlledVocabularyPatchBody(BasePatchBody, ControlledVocabularyFields):
    pass
