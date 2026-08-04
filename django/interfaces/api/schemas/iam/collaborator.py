import uuid
from typing import Optional, TYPE_CHECKING
from ninja import Query
from interfaces.api.schemas import BaseGetResponse, BasePostBody, CollectionQueryParameters

if TYPE_CHECKING:
    from interfaces.api.schemas import (
        RoleSummaryResponse,
        AccountContactDetailResponse,
        ServiceAccountContactResponse,
    )

DELETED_USER_CONTACT = {
    "name": "Deleted User",
    "email": "deleted-user@hydroserver.org",
    "organization_name": None,
    "phone": None,
    "address": None,
    "link": None,
    "user_type": "Unknown",
}


class CollaboratorQueryParameters(CollectionQueryParameters):
    role_id: list[uuid.UUID] = Query([], description="Filter collaborators by role ID.")


class CollaboratorDetailResponse(BaseGetResponse):
    user: Optional["AccountContactDetailResponse"] = None
    service_account: Optional["ServiceAccountContactResponse"] = None
    role: "RoleSummaryResponse"


class CollaboratorPostBody(BasePostBody):
    email: str
    role_id: uuid.UUID


class CollaboratorDeleteBody(BasePostBody):
    email: str
