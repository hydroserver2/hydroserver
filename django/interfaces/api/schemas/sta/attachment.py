from typing import Optional
from ninja import Field, Query
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    CollectionQueryParameters,
)


# TODO: Temporary bridge until API tagging shape is updated.
def tags_dict_to_list(value):
    """Bridges the JSONB {key: value} storage shape to the wire shape of list[{key,value}]."""

    if isinstance(value, dict):
        return [{"key": key, "value": val} for key, val in value.items()]

    return value


class FileAttachmentQueryParameters(CollectionQueryParameters):
    file_attachment_type: list[str] = Query([], description="Filter by file attachment type.", alias="type")


class TagGetResponse(BaseGetResponse):
    key: str
    value: str


class TagPostBody(BasePostBody):
    key: str = Field(..., max_length=255)
    value: str = Field(..., max_length=255)


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
