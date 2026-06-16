import uuid
from typing import Any, Literal, Optional
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    AccountContactDetailResponse,
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


class QualityControlOperationResponse(BaseGetResponse):
    id: uuid.UUID
    created_by: AccountContactDetailResponse
    order: int
    operation_type: OperationType
    created_at: ISODatetime
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None

    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by or DELETED_USER_CONTACT


class QualityControlOperationQueryParameters(CollectionQueryParameters):
    pass


class QualityControlOperationPostBody(BasePostBody):
    operation_type: OperationType
    order: int
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None


class QualityControlOperationPatchBody(BasePatchBody):
    order: int
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None
