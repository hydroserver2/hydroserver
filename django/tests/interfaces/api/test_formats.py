import orjson
import pytest

from ninja import Schema

from interfaces.api.formats import FORMATS, Format, ResponseDocument
from tests.core.sta.factories import UnitFactory
from tests.interfaces.api.helpers import set_collection_formats

pytestmark = pytest.mark.django_db

# A format plugs in by registering a Format and listing its key on collections: its media type, documentation,
# conformance classes and required fields take effect without changes elsewhere.

UNITS_PATH = "/api/ogc/collections/units/items"
CONFORMANCE_URI = "https://example.org/conf/test-format"


class CountDocument(Schema):
    count: int


class CountFormat(Format):
    """Encodes a response document as the number of items in it."""

    key = "count"
    media_type = "application/x-count+json"
    conformance = (CONFORMANCE_URI,)

    def required_fields(self, collection):
        return frozenset({"symbol"})

    def encode(self, document, context):
        items = [document.items] if document.is_item else document.items
        return orjson.dumps({"count": len(items), "items": items})

    def document_schema(self, collection, kind):
        return CountDocument


@pytest.fixture
def count_format(monkeypatch):
    monkeypatch.setitem(FORMATS, CountFormat.key, CountFormat())
    set_collection_formats(monkeypatch, ("units",), {"json": (), "count": ()})


@pytest.mark.usefixtures("count_format")
def test_a_registered_format_encodes_response_documents(client):
    UnitFactory(global_=True)

    response = client.get(UNITS_PATH, {"f": "count"})

    assert response["Content-Type"] == "application/x-count+json; charset=utf-8"
    assert response.json()["count"] == 1


@pytest.mark.usefixtures("count_format")
def test_a_format_keeps_its_required_fields_when_properties_leaves_them_out(client):
    unit = UnitFactory(global_=True)

    (item,) = client.get(UNITS_PATH, {"f": "count", "properties": "name"}).json()["items"]
    (json_item,) = client.get(UNITS_PATH, {"properties": "name"}).json()["data"]

    assert item == {"name": unit.name, "symbol": unit.symbol}
    assert json_item == {"name": unit.name}


@pytest.mark.usefixtures("count_format")
def test_a_format_documents_its_responses_and_conformance(client):
    paths = client.get("/api/ogc/openapi.json").json()["paths"]
    units_get = next(item["get"] for path, item in paths.items() if path.endswith("/units/items"))

    assert set(units_get["responses"]["200"]["content"]) == {"application/json", CountFormat.media_type}
    assert CONFORMANCE_URI in client.get("/api/ogc/conformance").json()["conformsTo"]


def test_response_document_reads_a_page_of_items():
    document = ResponseDocument.from_json(
        {"data": [{"id": 1}], "meta": {"limit": 10, "offset": 0, "totalCount": 3}, "links": [{"rel": "self"}]}
    )

    assert document.items == [{"id": 1}]
    assert not document.is_item
    assert document.number_matched == 3
    assert document.links == [{"rel": "self"}]
    assert document.included is None


def test_response_document_reads_an_item_with_included_resources():
    document = ResponseDocument.from_json({"data": {"id": 1}, "included": {"units": [{"id": 2}]}, "links": []})

    assert document.is_item
    assert document.number_matched is None
    assert document.included == {"units": [{"id": 2}]}
