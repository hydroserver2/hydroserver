import uuid

from typing import Optional, Literal, Annotated, cast
from pydantic import EmailStr, BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    UserContactResponse,
    RoleResponse,
    split_comma_separated,
    comma_array_schema,
)


class WorkspaceFields(Schema):
    name: str = Field(..., max_length=255)
    is_private: bool


WORKSPACE_INCLUDE_RELATIONS = {
    "owner": {
        "path": "owner",
        "bucket": "owners",
        "response_schema": UserContactResponse,
    },
    "pendingTransferTo": {
        "path": "pending_transfer_to",
        "bucket": "pendingTransferRecipients",
        "response_schema": UserContactResponse,
    },
    "collaboratorRole": {
        "path": "collaborator_role",
        "bucket": "collaboratorRoles",
        "response_schema": RoleResponse,
    },
}
WorkspaceIncludeRelation = Literal[*WORKSPACE_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "name",
    "isPrivate",
)
WorkspaceSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "ownerEmail",
    "pendingTransferToEmail",
    "collaboratorRoleId",
    *(to_camel(name) for name in cast(dict, WorkspaceFields.model_fields)),  # noqa
)
WorkspacePropertyName = Literal[*_property_fields]


class WorkspaceFilterFields(Schema):
    properties: Annotated[
        Optional[list[WorkspacePropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(WorkspacePropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[WorkspaceIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(WorkspaceIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class WorkspaceItemQueryParameters(WorkspaceFilterFields, BaseQueryParameters):
    pass


class WorkspaceQueryParameters(WorkspaceFilterFields, CollectionQueryParameters):
    sortby: Optional[list[WorkspaceSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    is_associated: Optional[bool] = Query(
        None,
        description="Whether the workspace is associated with the authenticated user",
    )
    is_private: Optional[bool] = Query(
        None, description="Whether the returned workspaces should be private or public."
    )


class WorkspaceResponse(BaseGetResponse, WorkspaceFields):
    id: uuid.UUID
    owner_email: str
    pending_transfer_to_email: Optional[str] = None
    collaborator_role_id: Optional[uuid.UUID] = None

    @staticmethod
    def resolve_owner_email(obj):
        if hasattr(obj, "owner_email"):
            return obj.owner_email

        return obj.owner.email

    @staticmethod
    def resolve_pending_transfer_to_email(obj):
        if hasattr(obj, "pending_transfer_to_email"):
            return obj.pending_transfer_to_email

        recipient = getattr(obj, "pending_transfer_to", None)

        return recipient.email if recipient else None

    @staticmethod
    def resolve_collaborator_role_id(obj):
        if hasattr(obj, "collaborator_role_id"):
            return obj.collaborator_role_id

        role = getattr(obj, "collaborator_role", None)

        return role.id if role else None


class WorkspacePostBody(BasePostBody, WorkspaceFields):
    id: Optional[uuid.UUID] = None


class WorkspacePatchBody(BasePatchBody, WorkspaceFields):
    pass


class WorkspaceTransferBody(BasePostBody):
    new_owner: EmailStr
