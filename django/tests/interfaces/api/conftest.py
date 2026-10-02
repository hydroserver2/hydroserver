import orjson
import pytest

from django.test import override_settings

from interfaces.api.formats import FORMATS, Format
from tests.interfaces.api.helpers import BASE_URL, set_collection_formats


class PlainTextFormat(Format):
    """A text/plain format (f=text) whose body is the JSON document, so tests can read its links."""

    key = "text"
    media_type = "text/plain"

    def __init__(self, links_in_body: bool = True):
        self.links_in_body = links_in_body

    def render(self, data, context):
        return orjson.dumps(data, default=str)


@pytest.fixture
def proxy_base_url():
    """Builds links from BASE_URL (tests.interfaces.api.helpers)."""

    with override_settings(PROXY_BASE_URL=BASE_URL):
        yield


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
