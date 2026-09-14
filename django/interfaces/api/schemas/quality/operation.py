import uuid

from typing import Any, Literal, Optional, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from ninja import Query, Schema

from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    UserContactResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.iam.collaborator import DELETED_USER_CONTACT

OperationType = Literal[
    "SELECTION",
    "VALUE_THRESHOLD",
    "DATETIME_RANGE",
    "CHANGE",
    "RATE_OF_CHANGE",
    "FIND_GAPS",
    "PERSISTENCE",
    "ADD_POINTS",
    "CHANGE_VALUES",
    "ASSIGN_VALUES_BULK",
    "DELETE_POINTS",
    "DRIFT_CORRECTION",
    "INTERPOLATE",
    "SHIFT_DATETIMES",
    "FILL_GAPS",
    "ASSIGN_DATETIMES_BULK",
]

_order_by_fields = ("id", "order", "operationType", "createdAt")
QualityControlOperationOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id",
    "createdBy",
    "order",
    "operationType",
    "createdAt",
    "comment",
    "arguments",
)
QualityControlOperationPropertyName = Literal[*_property_fields]


class QualityControlOperationFilterFields(Schema):
    properties: Annotated[
        Optional[list[QualityControlOperationPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(QualityControlOperationPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )


class QualityControlOperationItemQueryParameters(QualityControlOperationFilterFields, BaseQueryParameters):
    pass


class QualityControlOperationQueryParameters(QualityControlOperationFilterFields, CollectionQueryParameters):
    order_by: Optional[list[QualityControlOperationOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )


class QualityControlOperationResponse(BaseGetResponse):
    id: uuid.UUID
    created_by: UserContactResponse
    order: int
    operation_type: OperationType
    created_at: ISODatetime
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None

    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by or DELETED_USER_CONTACT


class QualityControlOperationPostBody(BasePostBody):
    operation_type: OperationType
    order: int
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None


class QualityControlOperationPatchBody(BasePatchBody):
    order: int
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None
