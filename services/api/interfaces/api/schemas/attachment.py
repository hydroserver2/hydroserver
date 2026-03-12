from typing import Optional
from ninja import Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)


class FileAttachmentQueryParameters(CollectionQueryParameters):
    type: list[str] = Query([], description="Filter by file attachment type.")


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
    description: str
    link: str
    file_attachment_type: str


class FileAttachmentDeleteBody(BasePostBody):
    name: str


class FileAttachmentPatchBody(BasePatchBody):
    name: Optional[str] = None
    description: Optional[str] = None
