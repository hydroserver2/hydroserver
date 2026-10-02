from dataclasses import replace

import orjson
import pytest

from interfaces.api import collections
from interfaces.api.collections import _COLLECTIONS_BY_ID
from interfaces.api.formats import FORMATS, Format
from interfaces.api.views import ogc


class PlainTextFormat(Format):
    """A text/plain format (f=text) whose body is the JSON document, so tests can read its links."""

    key = "text"
    media_type = "text/plain"

    def __init__(self, links_in_body: bool = True):
        self.links_in_body = links_in_body

    def render(self, data, context):
        return orjson.dumps(data, default=str)


@pytest.fixture
def plain_text_format(monkeypatch):
    """
    Registers a text/plain format (f=text) on the units and observations collections, so tests can exercise
    format negotiation and format links while JSON is the only real format. Its body is the JSON document
    under a text/plain content type, so tests can read its links.
    """

    def register(links_in_body: bool = True) -> Format:
        fmt = PlainTextFormat(links_in_body=links_in_body)
        monkeypatch.setitem(FORMATS, fmt.key, fmt)

        set_collection_formats(monkeypatch, ("units", "observations"), {"json": (), fmt.key: ()})

        return fmt

    return register


def set_collection_formats(monkeypatch, collection_ids, formats):
    """
    Replaces the formats of the given collections everywhere the registry is read. formats maps format keys to
    profile keys, as CollectionDefinition.formats does.
    """

    registry = tuple(
        replace(collection, formats=formats) if collection.id in collection_ids else collection
        for collection in collections.COLLECTIONS
    )

    for module in (collections, ogc):
        monkeypatch.setattr(module, "COLLECTIONS", registry)
    for collection in registry:
        monkeypatch.setitem(_COLLECTIONS_BY_ID, collection.id, collection)
