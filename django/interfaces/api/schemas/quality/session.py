import uuid
from ninja import Query
from typing import Literal, Optional
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    AccountContactDetailResponse,
)
from interfaces.api.schemas.quality.operation import QualityControlOperationResponse
from interfaces.api.schemas.iam.collaborator import DELETED_USER_CONTACT

SessionStatus = Literal["in_progress", "committed"]


class QualityControlSessionSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    history_id: uuid.UUID
    created_by: AccountContactDetailResponse
    created_at: ISODatetime
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    status: SessionStatus
    committed_at: Optional[ISODatetime] = None
    description: Optional[str] = None
    source_checksum: str
    managed_checksum: Optional[str] = None

    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by or DELETED_USER_CONTACT


class QualityControlSessionDetailResponse(BaseGetResponse):
    id: uuid.UUID
    history_id: uuid.UUID
    created_by: AccountContactDetailResponse
    created_at: ISODatetime
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    status: SessionStatus
    committed_at: Optional[ISODatetime] = None
    description: Optional[str] = None
    source_checksum: str
    managed_checksum: Optional[str] = None
    dependency_ids: list[uuid.UUID]
    operations: list[QualityControlOperationResponse]

    @staticmethod
    def resolve_created_by(obj):
        return obj.created_by or DELETED_USER_CONTACT

    @staticmethod
    def resolve_dependency_ids(obj):
        return [dependency.dependency_id for dependency in obj.dependencies.all()]

    @staticmethod
    def resolve_operations(obj):
        return list(obj.operations.all())


class QualityControlSessionQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    status: Optional[SessionStatus] = None
    range_start: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range start.")
    range_end: Optional[ISODatetime] = Query(None, description="Return sessions overlapping with this range end.")
    ancestor_of: Optional[uuid.UUID] = Query(None, description="Return all transitive ancestors of the given session ID.")
    include_ancestors: bool = Query(False, description="Also return transitive ancestors of all sessions matched by other filters.")


class QualityControlSessionPostBody(BasePostBody):
    phenomenon_time_start: ISODatetime
    phenomenon_time_end: ISODatetime
    description: Optional[str] = None


class QualityControlSessionPatchBody(BasePatchBody):
    description: Optional[str] = None
