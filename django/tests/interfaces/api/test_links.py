import re
import uuid

import pytest

from django.test import override_settings

from interfaces.api.collections import COLLECTIONS
from interfaces.api.http.links import build_collection_link
from interfaces.api.schemas import base
from interfaces.api.urls import api
from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory, UnitFactory
from tests.interfaces.api.helpers import BASE_URL, links_by_rel, query_params

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("proxy_base_url_with_trailing_slash")]

# List and item responses link to themselves (OGC API - Features Core Req 28 and 35) and pages
# link to the next and previous pages (Core Recs 17-19, Permission 7). Links are built from
# PROXY_BASE_URL, not the request's Host, which the test client sends as "testserver".

UNITS_PATH = "/api/ogc/collections/units/items"
OBSERVATIONS_PATH = "/api/ogc/collections/observations/items"


@pytest.fixture
def proxy_base_url_with_trailing_slash():
    """Sets PROXY_BASE_URL with a trailing slash, which links must not double."""

    with override_settings(PROXY_BASE_URL=f"{BASE_URL}/"):
        yield


@pytest.fixture
def max_limit_of_two(monkeypatch):
    monkeypatch.setattr(base, "MAX_LIMIT", 2)


def test_list_self_link_is_the_request_url_on_proxy_base_url(client):
    response = client.get(f"{UNITS_PATH}?limit=5&sortby=-name")

    assert response.status_code == 200
    assert links_by_rel(response)["self"] == {
        "href": f"{BASE_URL}{UNITS_PATH}?limit=5&sortby=-name",
        "rel": "self",
        "type": "application/json",
    }


def test_list_self_link_without_a_query_string_has_no_question_mark(client):
    response = client.get(UNITS_PATH)

    assert links_by_rel(response)["self"]["href"] == f"{BASE_URL}{UNITS_PATH}"


def test_item_links_to_itself_and_its_collection(client):
    unit = UnitFactory(global_=True)

    response = client.get(f"{UNITS_PATH}/{unit.id}", {"properties": "name"})

    assert response.status_code == 200
    assert response.json()["links"] == [
        {
            "href": f"{BASE_URL}{UNITS_PATH}/{unit.id}?properties=name",
            "rel": "self",
            "type": "application/json",
        },
        {
            "href": f"{BASE_URL}/api/ogc/collections/units",
            "rel": "collection",
            "type": "application/json",
        },
    ]


def test_item_collection_link_resolves_to_its_collection(client):
    site = MonitoringSiteFactory()

    response = client.get(f"/api/ogc/collections/monitoring-sites/items/{site.id}")
    collection_href = links_by_rel(response)["collection"]["href"]

    assert client.get(collection_href.removeprefix(BASE_URL)).json()["id"] == "monitoring-sites"


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_link_for_an_item_of_every_collection(rf, collection):
    request = rf.get(f"/api/ogc/collections/{collection.id}/items/{uuid.uuid4()}")

    assert build_collection_link(request).href == f"{BASE_URL}/api/ogc/collections/{collection.id}"


@pytest.mark.parametrize(
    "path",
    [
        f"/api/ogc/collections/quality-control-histories/items/{uuid.uuid4()}/sessions/{uuid.uuid4()}",
        f"/api/ogc/collections/etl-tasks/items/{uuid.uuid4()}/runs/{uuid.uuid4()}",
        f"/api/ogc/collections/workspaces/items/{uuid.uuid4()}/service-accounts/{uuid.uuid4()}",
        f"/api/ogc/collections/not-a-collection/items/{uuid.uuid4()}",
        "/api/ogc/collections/units/items",
    ],
)
def test_no_collection_link_outside_a_collection_item(rf, path):
    assert build_collection_link(rf.get(path)) is None


def test_full_first_page_links_next_but_not_prev(client):
    UnitFactory.create_batch(3, global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 2}))

    assert set(links) == {"self", "next"}
    assert query_params(links["next"]["href"]) == {"limit": ["2"], "offset": ["2"]}
    assert links["next"]["type"] == "application/json"


def test_middle_page_links_next_and_prev(client):
    UnitFactory.create_batch(5, global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 2, "offset": 2}))

    assert set(links) == {"self", "next", "prev"}
    assert query_params(links["next"]["href"])["offset"] == ["4"]
    assert query_params(links["prev"]["href"])["offset"] == ["0"]


def test_partial_last_page_links_prev_but_not_next(client):
    UnitFactory.create_batch(3, global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 2, "offset": 2}))

    assert set(links) == {"self", "prev"}


def test_prev_link_does_not_go_below_offset_zero(client):
    UnitFactory.create_batch(3, global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 2, "offset": 1}))

    assert query_params(links["prev"]["href"]) == {"limit": ["2"], "offset": ["0"]}


def test_zero_limit_links_only_self(client):
    UnitFactory(global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 0}))

    assert set(links) == {"self"}


def test_page_links_use_the_limit_that_was_applied(client, max_limit_of_two):
    UnitFactory.create_batch(3, global_=True)

    links = links_by_rel(client.get(UNITS_PATH, {"limit": 50}))

    assert query_params(links["self"]["href"])["limit"] == ["50"]
    assert query_params(links["next"]["href"])["limit"] == ["2"]


def test_page_links_keep_the_other_query_parameters(client):
    UnitFactory.create_batch(3, global_=True)

    response = client.get(
        f"{UNITS_PATH}?limit=2&properties=name&properties=symbol&sortby=-name,%2Bsymbol"
        "&datetime=2024-01-01T00%3A00%3A00Z%2F.."
    )

    assert response.status_code == 200
    assert query_params(links_by_rel(response)["next"]["href"]) == {
        "limit": ["2"],
        "offset": ["2"],
        "properties": ["name", "symbol"],
        "sortby": ["-name,+symbol"],
        "datetime": ["2024-01-01T00:00:00Z/.."],
    }


def test_following_next_links_returns_every_item_once(client):
    units = UnitFactory.create_batch(5, global_=True)
    seen = []
    url = f"{UNITS_PATH}?limit=2"

    while url:
        response = client.get(url)
        seen.extend(item["id"] for item in response.json()["data"])
        next_link = links_by_rel(response).get("next")
        url = next_link["href"].removeprefix(BASE_URL) if next_link else None

    assert sorted(seen) == sorted(str(unit.id) for unit in units)


@pytest.mark.parametrize("profile", ["https://hydroserver.org/profiles/observations/row", "https://hydroserver.org/profiles/observations/column"])
def test_observation_profiles_link_next_from_the_observations_on_the_page(client, profile):
    datastream = DatastreamFactory()
    ObservationFactory.create_batch(3, datastream=datastream)

    response = client.get(OBSERVATIONS_PATH, {"datastreamId": str(datastream.id), "profile": profile, "limit": 2})

    assert response.status_code == 200
    (group,) = response.json()["data"]
    assert len(group["rows"] if "rows" in group else group["columns"]["id"]) == 2
    assert set(links_by_rel(response)) == {"self", "alternate", "profile", "next"}


def _collection_items_paths():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]
    pattern = re.compile(r"/api/ogc/collections/[a-z-]+/items")

    return sorted(path for path in paths if pattern.fullmatch(path) and "get" in paths[path])


@pytest.mark.parametrize("path", _collection_items_paths())
def test_every_collection_links_to_itself(client, path):
    client.force_login(UserFactory())

    response = client.get(path)

    assert response.status_code == 200
    links = response.json()["links"]
    assert links_by_rel(response)["self"]["href"] == f"{BASE_URL}{path}"
    # Profile links identify a profile rather than a retrievable resource, so they have no media type.
    assert all({"href", "rel", "type"} <= set(link) for link in links if link["rel"] != "profile")


def test_links_are_documented_in_the_openapi_document():
    schemas = api.get_openapi_schema(path_prefix="/api/ogc/")["components"]["schemas"]

    assert schemas["Link"]["required"] == ["href", "rel"]
    assert "links" in schemas["PaginatedResponse_UnitResponse_"]["properties"]
