import uuid
from typing import Optional, Literal, Annotated

from ninja import Query, Schema
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    DatastreamResponse,
    split_comma_separated,
    comma_array_schema,
)


class EtlMappingFields(Schema):
    source_identifier: str
    target_datastream_id: uuid.UUID


_sortby_fields = ("id", "sourceIdentifier", "targetDatastreamId")

EtlMappingSortByFields = Literal[*_sortby_fields, *[f"-{f}" for f in _sortby_fields]]

_property_fields = (
    "id",
    *(to_camel(name) for name in EtlMappingFields.model_fields),
)
EtlMappingPropertyName = Literal[*_property_fields]

ETL_MAPPING_INCLUDE_RELATIONS = {
    "targetDatastream": {
        "path": "target_datastream",
        "bucket": "targetDatastreams",
        "response_schema": DatastreamResponse,
    },
}
EtlMappingIncludeRelation = Literal[*ETL_MAPPING_INCLUDE_RELATIONS.keys()]


class EtlMappingFilterFields(Schema):
    """
    Shared by both the list and single-item query parameter classes so
    `properties`/`include` are validated identically regardless of endpoint.
    """

    properties: Annotated[
        Optional[list[EtlMappingPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(EtlMappingPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[EtlMappingIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(EtlMappingIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class EtlMappingItemQueryParameters(EtlMappingFilterFields, BaseQueryParameters):
    pass


class EtlMappingQueryParameters(EtlMappingFilterFields, CollectionQueryParameters):
    sortby: Optional[list[EtlMappingSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    source_identifier: list[str] = Query(
        [], description="Filter mappings by source identifier."
    )
    target_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter mappings by target datastream ID."
    )
    etl_task_id: list[uuid.UUID] = Query(
        [], description="Filter mappings by ETL task ID."
    )
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter mappings by workspace ID."
    )


class EtlMappingResponse(BaseGetResponse, EtlMappingFields):
    id: uuid.UUID
    etl_task_id: uuid.UUID


class EtlMappingPostBody(BasePostBody, EtlMappingFields):
    id: Optional[uuid.UUID] = None
    etl_task_id: uuid.UUID


class EtlMappingPatchBody(BasePatchBody, EtlMappingFields):
    pass
