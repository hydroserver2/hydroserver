import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from ninja import Query, Schema

from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    DatastreamResponse,
    split_comma_separated,
    comma_array_schema,
)


QUALITY_CONTROL_HISTORY_INCLUDE_RELATIONS = {
    "managedDatastream": {
        "path": "managed_datastream",
        "bucket": "managedDatastreams",
        "response_schema": DatastreamResponse,
    },
    "sourceDatastream": {
        "path": "source_datastream",
        "bucket": "sourceDatastreams",
        "response_schema": DatastreamResponse,
    },
}
QualityControlHistoryIncludeRelation = Literal[
    *QUALITY_CONTROL_HISTORY_INCLUDE_RELATIONS.keys()
]

_order_by_fields = ("id", "createdAt", "phenomenonTimeStart", "phenomenonTimeEnd")
QualityControlHistoryOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id",
    "managedDatastreamId",
    "sourceDatastreamId",
    "createdAt",
    "phenomenonTimeStart",
    "phenomenonTimeEnd",
    "sourceChecksum",
    "managedChecksum",
)
QualityControlHistoryPropertyName = Literal[*_property_fields]


class QualityControlHistoryFilterFields(Schema):
    properties: Annotated[
        Optional[list[QualityControlHistoryPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(QualityControlHistoryPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[QualityControlHistoryIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(QualityControlHistoryIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class QualityControlHistoryItemQueryParameters(
    QualityControlHistoryFilterFields, BaseQueryParameters
):
    pass


class QualityControlHistoryQueryParameters(
    QualityControlHistoryFilterFields, CollectionQueryParameters
):
    order_by: Optional[list[QualityControlHistoryOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    managed_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter histories by managed datastream ID."
    )
    source_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter histories by source datastream ID."
    )


class QualityControlHistoryResponse(BaseGetResponse):
    id: uuid.UUID
    managed_datastream_id: uuid.UUID
    source_datastream_id: uuid.UUID
    created_at: ISODatetime
    phenomenon_time_start: Optional[ISODatetime] = None
    phenomenon_time_end: Optional[ISODatetime] = None
    source_checksum: Optional[str] = None
    managed_checksum: Optional[str] = None


class QualityControlHistoryPostBody(BasePostBody):
    managed_datastream_id: uuid.UUID
    source_datastream_id: uuid.UUID
