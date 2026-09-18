import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    CreatedResponse,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
)


class ServiceAccountInputFields(Schema):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_active: bool
    key_expires_at: Optional[ISODatetime] = None


class ServiceAccountFields(ServiceAccountInputFields):
    email: str
    created_at: ISODatetime
    last_used_at: Optional[ISODatetime]


SERVICE_ACCOUNT_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
ServiceAccountIncludeRelation = Literal[*SERVICE_ACCOUNT_INCLUDE_RELATIONS.keys()]


_sortby_fields = (
    "name",
    "isActive",
    "keyExpiresAt",
    "createdAt",
    "lastUsedAt",
)
ServiceAccountSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]


_property_fields = (
    "id",
    "workspaceId",
    *(to_camel(name) for name in ServiceAccountFields.model_fields),
)
ServiceAccountPropertyName = Literal[*_property_fields]


class ServiceAccountFilterFields(Schema):
    properties: Annotated[
        Optional[list[ServiceAccountPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ServiceAccountPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ServiceAccountIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ServiceAccountIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ServiceAccountItemQueryParameters(ServiceAccountFilterFields, BaseQueryParameters):
    pass


class ServiceAccountQueryParameters(ServiceAccountFilterFields, CollectionQueryParameters):
    sortby: Optional[list[ServiceAccountSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )


class ServiceAccountResponse(BaseGetResponse, ServiceAccountFields):
    id: uuid.UUID
    workspace_id: uuid.UUID


class ServiceAccountCreatedResponse(CreatedResponse):
    key: str = Field(..., max_length=255)


class ServiceAccountKeyResponse(BaseGetResponse):
    key: str = Field(..., max_length=255)


class ServiceAccountPostBody(BasePostBody, ServiceAccountInputFields):
    id: Optional[uuid.UUID] = None
    role_id: Optional[uuid.UUID] = None


class ServiceAccountPatchBody(BasePatchBody, ServiceAccountInputFields):
    pass


class ServiceAccountContactResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    email: str
