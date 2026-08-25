import uuid
from typing import Optional
from ninja import Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    CollectionQueryParameters,
)


class LinkedResourceQueryParameters(CollectionQueryParameters):
    type: list[str] = Query([], description="Filter by linked resource type.")


class TagGetResponse(BaseGetResponse):
    key: str
    value: str


class TagPostBody(BasePostBody):
    key: str
    value: str


class TagDeleteBody(BasePostBody):
    key: str
    value: Optional[str] = None


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
