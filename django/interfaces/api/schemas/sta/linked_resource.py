from typing import Optional
from ninja import Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    PaginatedQueryParameters,
)
from interfaces.api.schemas.base import ItemId


class LinkedResourceQueryParameters(PaginatedQueryParameters):
    type: list[str] = Query(
        [],
        description="Linked resources of this type. Matches `name` in `linked-resource-types`.",
    )


class LinkedResourceGetResponse(BaseGetResponse, ItemId):
    name: str
    description: Optional[str] = None
    type: str
    link: str


class LinkedResourcePostBody(BasePostBody):
    name: str
    description: Optional[str] = None
    type: str
