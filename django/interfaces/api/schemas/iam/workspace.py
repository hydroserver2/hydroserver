import uuid
from typing import Optional, Literal, TYPE_CHECKING
from ninja import Schema, Field, Query
from pydantic import EmailStr
from django.contrib.auth import get_user_model
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import RoleDetailResponse


User = get_user_model()


class WorkspaceFields(Schema):
    name: str = Field(..., max_length=255)
    is_private: bool


_order_by_fields = (
    "name",
    "isPrivate",
)

WorkspaceOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class WorkspaceQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[WorkspaceOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    is_associated: Optional[bool] = Query(
        None,
        description="Whether the workspace is associated with the authenticated user",
    )
    is_private: Optional[bool] = Query(
        None, description="Whether the returned workspaces should be private or public."
    )


class UserContactFields(Schema):
    phone: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=255)
    link: Optional[str] = Field(None, max_length=2000)
    user_type: str = Field(..., max_length=255, alias="type")


class AccountContactDetailResponse(BaseGetResponse, UserContactFields):
    name: str = Field(..., max_length=255)
    email: EmailStr
    organization_name: Optional[str] = None


class WorkspaceSummaryResponse(BaseGetResponse, WorkspaceFields):
    id: uuid.UUID


class WorkspaceDetailResponse(BaseGetResponse, WorkspaceFields):
    id: uuid.UUID
    owner: AccountContactDetailResponse
    collaborator_role: Optional["RoleDetailResponse"] = None
    pending_transfer_to: Optional[AccountContactDetailResponse] = None


class WorkspacePostBody(BasePostBody, WorkspaceFields):
    id: Optional[uuid.UUID] = None


class WorkspacePatchBody(BasePatchBody, WorkspaceFields):
    pass


class WorkspaceTransferBody(BasePostBody):
    new_owner: EmailStr
