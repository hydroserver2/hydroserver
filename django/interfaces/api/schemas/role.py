import uuid
from ninja import Schema, Field, Query
from typing import Optional, Literal, TYPE_CHECKING
from interfaces.api.schemas import BaseGetResponse, CollectionQueryParameters
from domains.iam.models.permission import PERMISSION_CHOICES, RESOURCE_TYPE_CHOICES

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceDetailResponse

RESOURCE_TYPES = Literal[*[choice[0] for choice in RESOURCE_TYPE_CHOICES]]
PERMISSIONS = Literal[*[choice[0] for choice in PERMISSION_CHOICES]]


class PermissionDetailResponse(BaseGetResponse):
    resource_type: RESOURCE_TYPES = Field(..., alias="resource")
    permission_type: PERMISSIONS = Field(..., alias="action")


class RoleFields(Schema):
    name: str = Field(..., max_length=255)
    description: str
    is_user_role: bool
    is_apikey_role: bool = Field(..., validation_alias="isAPIKeyRole")


_order_by_fields = (
    "name",
    "isUserRole",
    "isAPIKeyRole",
)

RoleOrderByFields = Literal[*_order_by_fields, *[f"-{f}" for f in _order_by_fields]]


class RoleQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[RoleOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter roles by workspace ID."
    )
    is_user_role: Optional[bool] = Query(
        None, description="Controls whether the returned roles should be user roles."
    )
    is_apikey_role: Optional[bool] = Query(
        None, description="Controls whether the returned roles should be API key roles."
    )


class RoleSummaryResponse(BaseGetResponse, RoleFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]
    permissions: list[PermissionDetailResponse]


class RoleDetailResponse(BaseGetResponse, RoleFields):
    id: uuid.UUID
    workspace: Optional["WorkspaceDetailResponse"]
    permissions: list[PermissionDetailResponse]
