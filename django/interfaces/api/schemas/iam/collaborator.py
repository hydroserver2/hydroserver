import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema, ConfigDict
from pydantic.alias_generators import to_camel
from ninja import Schema, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    CollectionQueryParameters,
    RoleResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.iam.user import UserContactResponse
from interfaces.api.schemas.iam.service_account import ServiceAccountContactResponse

DELETED_USER_CONTACT = {
    "name": "Deleted User",
    "email": "deleted-user@hydroserver.org",
    "organization_name": None,
    "phone": None,
    "address": None,
    "link": None,
    "user_type": "Unknown",
}

COLLABORATOR_INCLUDE_RELATIONS = {
    "role": {
        "path": "role",
        "bucket": "roles",
        "response_schema": RoleResponse,
    },
    "user": {
        "path": "user",
        "bucket": "users",
        "response_schema": UserContactResponse,
    },
    "serviceAccount": {
        "path": "service_account",
        "bucket": "serviceAccounts",
        "response_schema": ServiceAccountContactResponse,
    },
}
CollaboratorIncludeRelation = Literal[*COLLABORATOR_INCLUDE_RELATIONS.keys()]

_property_fields = ("roleId", "userEmail", "serviceAccountEmail")
CollaboratorPropertyName = Literal[*_property_fields]

_sortby_fields = ("id", "roleId")
CollaboratorSortByFields = Literal[*_sortby_fields, *[f"-{f}" for f in _sortby_fields]]


class CollaboratorFilterFields(Schema):
    properties: Annotated[
        Optional[list[CollaboratorPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(CollaboratorPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[CollaboratorIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(CollaboratorIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class CollaboratorQueryParameters(CollaboratorFilterFields, CollectionQueryParameters):
    role_id: list[uuid.UUID] = Query([], description="Filter collaborators by role ID.")
    sortby: Optional[list[CollaboratorSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )


class CollaboratorResponse(BaseGetResponse):
    role_id: uuid.UUID
    user_email: Optional[str] = None
    service_account_email: Optional[str] = None

    @staticmethod
    def resolve_user_email(obj):
        if hasattr(obj, "user_email"):
            return obj.user_email

        return obj.user.email if obj.user else None

    @staticmethod
    def resolve_service_account_email(obj):
        if hasattr(obj, "service_account_email"):
            return obj.service_account_email

        return obj.service_account.email if obj.service_account else None


class CollaboratorPostBody(BasePostBody):
    email: str
    role_id: uuid.UUID


class CollaboratorDeleteBody(BasePostBody):
    email: str


class CollaboratorCreatedResponse(Schema):
    id: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
