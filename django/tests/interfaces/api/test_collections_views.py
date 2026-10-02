import pytest

from django.test import override_settings

from interfaces.api.collections import COLLECTIONS
from interfaces.api.urls import api
from tests.core.iam.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("proxy_base_url")]

# /collections lists every collection and /collections/{collectionId} describes one, each with
# self and items links (OGC API - Features Core Req 11-15, 18-19). Links are built from
# PROXY_BASE_URL, not the request's Host, which the test client sends as "testserver".

BASE_URL = "https://hydroserver.example.org"
COLLECTIONS_PATH = "/api/ogc/collections"
COLLECTION_IDS = [collection.id for collection in COLLECTIONS]
FEATURE_COLLECTION_IDS = ["workspaces", "monitoring-sites", "datastreams", "observations"]


@pytest.fixture
def proxy_base_url():
    with override_settings(PROXY_BASE_URL=BASE_URL):
        yield


def _links(body):
    return {link["rel"]: link for link in body["links"]}


def test_get_collections_links_to_itself(client):
    response = client.get(COLLECTIONS_PATH)

    assert response.status_code == 200
    assert response.json()["links"] == [
        {"href": f"{BASE_URL}{COLLECTIONS_PATH}", "rel": "self", "type": "application/json"}
    ]


def test_get_collections_lists_every_registered_collection_in_order(client):
    response = client.get(COLLECTIONS_PATH)

    assert [collection["id"] for collection in response.json()["collections"]] == COLLECTION_IDS


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_describes_the_registered_collection(client, collection):
    response = client.get(f"{COLLECTIONS_PATH}/{collection.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == collection.id
    assert body["title"] == collection.title
    assert body["description"] == collection.description
    assert body["itemType"] == collection.item_type
    items_href = f"{BASE_URL}{COLLECTIONS_PATH}/{collection.id}/items"
    items_links = [{"href": items_href, "rel": "items", "type": "application/json"}]
    if collection.item_type == "feature":
        items_links.append({"href": f"{items_href}?f=geojson", "rel": "items", "type": "application/geo+json"})
    assert body["links"] == [
        {"href": f"{BASE_URL}{COLLECTIONS_PATH}/{collection.id}", "rel": "self", "type": "application/json"},
        *items_links,
    ]


@pytest.mark.parametrize("collection_id", COLLECTION_IDS)
def test_collection_matches_its_entry_in_collections(client, collection_id):
    listed = {
        collection["id"]: collection for collection in client.get(COLLECTIONS_PATH).json()["collections"]
    }

    response = client.get(f"{COLLECTIONS_PATH}/{collection_id}")

    assert response.json() == listed[collection_id]


def test_feature_collections_are_the_spatial_collections():
    # A missing itemType means "feature" (Features Core collection.yaml), so a collection
    # switching type silently changes which collections OGC clients treat as features.
    assert {collection.id for collection in COLLECTIONS if collection.item_type == "feature"} == set(
        FEATURE_COLLECTION_IDS
    )


@pytest.mark.parametrize("collection_id", FEATURE_COLLECTION_IDS)
def test_feature_collection_declares_its_item_type(client, collection_id):
    response = client.get(f"{COLLECTIONS_PATH}/{collection_id}")

    assert response.json()["itemType"] == "feature"


def test_non_spatial_collection_declares_resource_item_type(client):
    response = client.get(f"{COLLECTIONS_PATH}/units")

    assert response.json()["itemType"] == "resource"


def test_get_collections_declares_an_item_type_for_every_collection(client):
    response = client.get(COLLECTIONS_PATH)

    assert {collection["itemType"] for collection in response.json()["collections"]} <= {
        "feature",
        "resource",
    }


@pytest.mark.parametrize("collection_id", COLLECTION_IDS)
def test_collection_items_link_resolves(client, collection_id):
    client.force_login(UserFactory())
    items_href = _links(client.get(f"{COLLECTIONS_PATH}/{collection_id}").json())["items"]["href"]

    response = client.get(items_href.removeprefix(BASE_URL))

    assert response.status_code == 200


def test_get_unknown_collection_returns_404(client):
    response = client.get(f"{COLLECTIONS_PATH}/not-a-collection")

    assert response.status_code == 404
    assert response.json() == {"message": "Collection 'not-a-collection' does not exist"}


@pytest.mark.parametrize("path", [COLLECTIONS_PATH, f"{COLLECTIONS_PATH}/units"])
def test_collections_endpoints_reject_unknown_query_parameters(client, path):
    response = client.get(path, {"foo": "bar"})

    assert response.status_code == 400


@pytest.mark.parametrize("path", [COLLECTIONS_PATH, f"{COLLECTIONS_PATH}/units"])
def test_collections_endpoints_are_public(client, path):
    response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize("path", [COLLECTIONS_PATH, f"{COLLECTIONS_PATH}/{{collection_id}}"])
def test_collections_endpoints_are_documented_under_collections(path):
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]

    assert paths[path]["get"]["tags"] == ["Collections"]


def test_collection_metadata_is_documented_once_for_all_collections():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]

    assert not [path for path in paths if path.removeprefix(f"{COLLECTIONS_PATH}/") in COLLECTION_IDS]


def test_openapi_operation_ids_are_unique():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]
    operation_ids = [operation["operationId"] for path in paths.values() for operation in path.values()]

    assert len(operation_ids) == len(set(operation_ids))
