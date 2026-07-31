import uuid
from typing import Optional, Literal, TYPE_CHECKING
from ninja import Schema, Field, Query
from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse


class ServiceAccountFields(Schema):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_active: bool
    key_expires_at: Optional[ISODatetime] = None


_order_by_fields = (
    "name",
    "isActive",
    "keyExpiresAt",
)

ServiceAccountOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class ServiceAccountQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[ServiceAccountOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )


class ServiceAccountGetFields(ServiceAccountFields):
    email: str
    created_at: ISODatetime
    last_used_at: Optional[ISODatetime]


class ServiceAccountSummaryResponse(BaseGetResponse, ServiceAccountGetFields):
    id: uuid.UUID
    workspace_id: uuid.UUID


class ServiceAccountDetailResponse(BaseGetResponse, ServiceAccountGetFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse"


class ServiceAccountSummaryPostResponse(
    ServiceAccountSummaryResponse, ServiceAccountGetFields
):
    key: str = Field(..., max_length=255)


class ServiceAccountDetailPostResponse(
    ServiceAccountDetailResponse, ServiceAccountGetFields
):
    key: str = Field(..., max_length=255)


class ServiceAccountPostBody(BasePostBody, ServiceAccountFields):
    id: Optional[uuid.UUID] = None


class ServiceAccountPatchBody(BasePatchBody, ServiceAccountFields):
    pass


class ServiceAccountContactResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    email: str
