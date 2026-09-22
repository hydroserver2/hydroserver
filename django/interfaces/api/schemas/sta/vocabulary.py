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
    split_comma_separated,
    comma_array_schema,
)


class VocabularyFields(Schema):
    name: str = Field(..., max_length=255)
    description: str = ""


_sortby_fields = ("name",)
VocabularySortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    *(to_camel(name) for name in VocabularyFields.model_fields),
)
VocabularyPropertyName = Literal[*_property_fields]


class VocabularyFilterFields(Schema):
    properties: Annotated[
        Optional[list[VocabularyPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(VocabularyPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )


class VocabularyItemQueryParameters(
    VocabularyFilterFields, BaseQueryParameters
):
    pass


class VocabularyQueryParameters(
    VocabularyFilterFields, CollectionQueryParameters
):
    sortby: Optional[list[VocabularySortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )


class VocabularyResponse(BaseGetResponse, VocabularyFields):
    id: uuid.UUID


class VocabularyPostBody(BasePostBody, VocabularyFields):
    id: Optional[uuid.UUID] = None


class VocabularyPatchBody(BasePatchBody, VocabularyFields):
    pass
