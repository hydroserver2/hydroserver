import uuid

from typing import Literal, Optional, Annotated
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

SessionStatus = Literal["in_progress", "committed"]

_sortby_fields = (
    "id",
    "createdAt",
    "phenomenonTimeStart",
    "phenomenonTimeEnd",
    "status",
    "committedAt",
)
QualityControlSessionSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "historyId",
    "createdBy",
    "createdAt",
    "phenomenonTimeStart",
    "phenomenonTimeEnd",
    "status",
    "committedAt",
    "description",
    "sourceChecksum",
    "managedChecksum",
    "dependencyIds",
)
QualityControlSessionPropertyName = Literal[*_property_fields]


class QualityControlSessionFilterFields(Schema):
    properties: Annotated[
        Optional[list[QualityControlSessionPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(QualityControlSessionPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )


class QualityControlSessionItemQueryParameters(QualityControlSessionFilterFields, BaseQueryParameters):
    pass


class QualityControlSessionQueryParameters(QualityControlSessionFilterFields, CollectionQueryParameters):
    sortby: Optional[list[QualityControlSessionSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    status: Optional[SessionStatus] = None
    range_start: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range start.")
    range_end: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range end.")
    ancestor_of: Optional[uuid.UUID] = Query(None, description="Return all transitive ancestors of the given session ID.")
    include_ancestors: bool = Query(False, description="Also return transitive ancestors of all sessions matched by other filters.")


class QualityControlSessionResponse(BaseGetResponse):
    id: uuid.UUID
    history_id: uuid.UUID
    created_by: UserContactResponse
    created_at: ISODatetime
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    status: SessionStatus
    committed_at: Optional[ISODatetime] = None
    description: Optional[str] = None
    source_checksum: str
    managed_checksum: Optional[str] = None
    dependency_ids: list[uuid.UUID]

    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by or DELETED_USER_CONTACT

    @staticmethod
    def resolve_dependency_ids(obj):
        if not hasattr(obj, "dependencies"):
            return getattr(obj, "dependency_ids", [])
        return [dependency.dependency_id for dependency in obj.dependencies.all()]


class QualityControlSessionPostBody(BasePostBody):
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    description: Optional[str] = None


class QualityControlSessionPatchBody(BasePatchBody):
    description: Optional[str] = None
