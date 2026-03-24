from typing import Optional
from ninja import Query
from core.interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    CollectionQueryParameters,
)


class FileAttachmentQueryParameters(CollectionQueryParameters):
    file_attachment_type: list[str] = Query([], description="Filter by file attachment type.", alias="type")


class TagGetResponse(BaseGetResponse):
    key: str
    value: str


class TagPostBody(BasePostBody):
    key: str
    value: str


class TagDeleteBody(BasePostBody):
    key: str
    value: Optional[str] = None


class FileAttachmentGetResponse(BaseGetResponse):
    id: int
    name: str
    description: Optional[str] = None
    link: str
    file_attachment_type: str


class FileAttachmentPostBody(BasePostBody):
    name: str
    description: Optional[str] = None
    file_attachment_type: str


class FileAttachmentDeleteBody(BasePostBody):
    name: str
