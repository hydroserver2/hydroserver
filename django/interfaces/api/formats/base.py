from dataclasses import dataclass
from typing import Any, Literal, Optional

from django.http import HttpRequest
from pydantic import BaseModel

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.document import ResponseDocument

DocumentKind = Literal["items", "item"]


@dataclass(frozen=True)
class EncodeContext:
    """What a format encodes a response document for."""

    request: HttpRequest
    collection: CollectionDefinition
    status: int


class Format:
    """
    A response format of collection items, selected by the f parameter value key or the Accept header. A format
    owns everything that differs between formats: how it encodes response documents, which item fields its media
    type requires, how its responses are documented and which conformance classes it implements.
    """

    key: str
    media_type: str
    # Formats that can't carry links in the body, such as CSV, send them in a Link header (RFC 8288).
    links_in_body: bool = True
    conformance: tuple[str, ...] = ()

    @property
    def content_type(self) -> str:
        return f"{self.media_type}; charset=utf-8"

    def required_fields(self, collection: CollectionDefinition) -> frozenset[str]:
        """
        Item fields the media type requires, kept even when the properties parameter leaves them out
        (OGC API - Features Part 6, /per/properties/required-properties).
        """

        return frozenset()

    def render(self, data: Any, context: EncodeContext) -> bytes:
        """Encodes the serialized JSON response document of a collection's items or item."""

        return self.encode(ResponseDocument.from_json(data), context)

    def encode(self, document: ResponseDocument, context: EncodeContext) -> bytes:
        raise NotImplementedError

    def document_schema(self, collection: CollectionDefinition, kind: DocumentKind) -> Optional[type[BaseModel]]:
        """The model that documents the format's responses in the OpenAPI document, if the format adds one."""

        return None
