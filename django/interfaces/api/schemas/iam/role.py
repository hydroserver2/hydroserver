import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from core.iam.models.permission import PERMISSION_CHOICES
from core.iam.permissions.registry import resource_types
from interfaces.api.schemas import (
    BaseGetResponse,
    BaseQueryParameters,
    CollectionQueryParameters,
    split_comma_separated,
    comma_array_schema,
)

RESOURCE_TYPES = Literal["*", *resource_types]
PERMISSIONS = Literal[*[choice[0] for choice in PERMISSION_CHOICES]]


class RoleFields(Schema):
    name: str = Field(..., max_length=255)
    description: str | None = None


class PermissionResponse(BaseGetResponse):
    resource_type: RESOURCE_TYPES = Field(..., alias="resource")
    permission_type: PERMISSIONS = Field(..., alias="action")


_sortby_fields = ("name",)
RoleSortByFields = Literal[*_sortby_fields, *[f"-{f}" for f in _sortby_fields]]

_property_fields = (
    "id",
    "workspaceId",
    *(to_camel(name) for name in RoleFields.model_fields),
    "permissions",
)
RolePropertyName = Literal[*_property_fields]


class RoleFilterFields(Schema):
    properties: Annotated[
        Optional[list[RolePropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(RolePropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )


class RoleItemQueryParameters(RoleFilterFields, BaseQueryParameters):
    pass


class RoleQueryParameters(RoleFilterFields, CollectionQueryParameters):
    sortby: Optional[list[RoleSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter roles by workspace ID."
    )


class RoleResponse(BaseGetResponse, RoleFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]
    permissions: list[PermissionResponse]

    @staticmethod
    def resolve_permissions(obj):
        permissions = getattr(obj, "permissions", None)
        if not hasattr(permissions, "all"):
            return permissions

        actions = ("view", "create", "edit", "delete")

        return [
            {"resource": permission.resource_type, "action": action}
            for permission in permissions.all()
            for action in actions
            if getattr(permission, f"can_{action}")
        ]
