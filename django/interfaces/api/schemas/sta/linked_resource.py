import uuid
from typing import Optional
from ninja import Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    PaginatedQueryParameters,
)


class LinkedResourceQueryParameters(PaginatedQueryParameters):
    type: list[str] = Query([], description="Filter by linked resource type.")


class LinkedResourceGetResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: str
    link: str


class LinkedResourcePostBody(BasePostBody):
    name: str
    description: Optional[str] = None
    type: str
