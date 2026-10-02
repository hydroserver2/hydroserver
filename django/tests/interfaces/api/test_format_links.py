from urllib.parse import parse_qs, urlsplit

import orjson
import pytest

from django.test import override_settings

from core.sta.models import DatastreamLinkedResource
from tests.core.iam.factories import WorkspaceFactory
from tests.interfaces.api.conftest import set_collection_formats
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, UnitFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("proxy_base_url")]

# Links name the media type of their target and carry the f parameter that selects it, and responses link to
# themselves in every other format of their collection (OGC API - Features Core Req 15, 28, 29 and 35). Links
# to the default format leave f out. The plain_text_format fixture registers a second format, text/plain
# (f=text), on units and observations.

BASE_URL = "https://hydroserver.example.org"
COLLECTIONS_PATH = "/api/ogc/collections"
UNITS_PATH = f"{COLLECTIONS_PATH}/units/items"
JSON = "application/json"
TEXT = "text/plain"


@pytest.fixture
def proxy_base_url():
    with override_settings(PROXY_BASE_URL=BASE_URL):
        yield


@pytest.fixture
def text_format(plain_text_format):
    return plain_text_format()


def _links(response, rel):
    body = orjson.loads(response.content)
    return [link for link in body["links"] if link["rel"] == rel]


def _link(response, rel):
    (link,) = _links(response, rel)
    return link


def _query(href):
    return {key: values[0] for key, values in parse_qs(urlsplit(href).query).items()}


def _follow(client, href):
    parts = urlsplit(href)
    return client.get(f"{parts.path}?{parts.query}")


def _two_units():
    UnitFactory(global_=True, name="Liter")
    UnitFactory(global_=True, name="Meter")


@pytest.mark.usefixtures("text_format")
def test_default_format_links_to_itself_without_f_and_to_its_alternates(client):
    _two_units()

    response = client.get(UNITS_PATH, {"limit": 1})

    assert _link(response, "self") == {"href": f"{BASE_URL}{UNITS_PATH}?limit=1", "rel": "self", "type": JSON}
    alternate = _link(response, "alternate")
    assert alternate["type"] == TEXT
    assert _query(alternate["href"]) == {"limit": "1", "f": "text"}
    assert _link(response, "next")["type"] == JSON
    assert "f" not in _query(_link(response, "next")["href"])


@pytest.mark.usefixtures("text_format")
def test_format_selected_by_accept_links_with_f(client):
    _two_units()

    response = client.get(UNITS_PATH, {"limit": 1}, headers={"Accept": TEXT})

    assert response["Content-Type"] == f"{TEXT}; charset=utf-8"
    for rel in ("self", "next"):
        link = _link(response, rel)
        assert link["type"] == TEXT
        assert _query(link["href"])["f"] == "text"
    alternate = _link(response, "alternate")
    assert alternate["type"] == JSON
    assert _query(alternate["href"]) == {"limit": "1", "f": "json"}


def test_explicit_f_stays_in_the_self_link(client):
    response = client.get(UNITS_PATH, {"f": "json"})

    assert _link(response, "self")["href"] == f"{BASE_URL}{UNITS_PATH}?f=json"


@pytest.mark.usefixtures("text_format")
def test_following_format_links_returns_their_format(client):
    _two_units()

    response = client.get(UNITS_PATH, {"limit": 1})
    text_page = _follow(client, _link(response, "alternate")["href"])
    next_text_page = _follow(client, _link(text_page, "next")["href"])

    assert text_page["Content-Type"] == f"{TEXT}; charset=utf-8"
    assert next_text_page["Content-Type"] == f"{TEXT}; charset=utf-8"
    assert orjson.loads(next_text_page.content)["data"][0]["name"] == "Meter"


@pytest.mark.usefixtures("text_format")
def test_item_links_to_its_alternates_and_its_json_collection(client):
    unit = UnitFactory(global_=True)

    response = client.get(f"{UNITS_PATH}/{unit.id}", headers={"Accept": TEXT})

    assert _link(response, "self")["type"] == TEXT
    assert _query(_link(response, "self")["href"]) == {"f": "text"}
    assert _link(response, "alternate")["type"] == JSON
    assert _link(response, "collection") == {
        "href": f"{BASE_URL}{COLLECTIONS_PATH}/units",
        "rel": "collection",
        "type": JSON,
    }


@pytest.mark.usefixtures("text_format")
def test_collection_links_to_its_items_in_every_format(client):
    response = client.get(f"{COLLECTIONS_PATH}/units")

    assert _links(response, "items") == [
        {"href": f"{BASE_URL}{COLLECTIONS_PATH}/units/items", "rel": "items", "type": JSON},
        {"href": f"{BASE_URL}{COLLECTIONS_PATH}/units/items?f=text", "rel": "items", "type": TEXT},
    ]
    listed = {collection["id"]: collection for collection in client.get(COLLECTIONS_PATH).json()["collections"]}
    assert listed["units"] == response.json()


def test_single_format_responses_have_no_alternates(client):
    UnitFactory(global_=True)

    assert _links(client.get(UNITS_PATH), "alternate") == []
    assert len(_links(client.get(f"{COLLECTIONS_PATH}/units"), "items")) == 1


def test_formats_without_links_in_the_body_send_a_link_header(client, plain_text_format):
    plain_text_format(links_in_body=False)
    _two_units()

    response = client.get(UNITS_PATH, {"limit": 1}, headers={"Accept": TEXT})

    assert f'<{BASE_URL}{UNITS_PATH}?limit=1&f=text>; rel="self"; type="{TEXT}"' in response["Link"]
    assert 'rel="alternate"; type="application/json"' in response["Link"]
    assert 'rel="next"' in response["Link"]
    assert not client.get(UNITS_PATH).has_header("Link")


def test_routes_outside_collection_items_have_no_alternates(client, monkeypatch, plain_text_format):
    plain_text_format()
    set_collection_formats(monkeypatch, ("datastreams",), {"json": (), "text": ()})
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    DatastreamLinkedResource.objects.create(datastream=datastream, name="A", type="Report", url="https://example.com/a")

    response = client.get(f"{COLLECTIONS_PATH}/datastreams/items/{datastream.id}/linked-resources")

    assert response.status_code == 200
    assert _links(response, "alternate") == []
    assert _link(response, "self")["type"] == JSON
