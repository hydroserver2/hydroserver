import pytest

from interfaces.api.collections import COLLECTIONS
from interfaces.api.urls import api
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory
from tests.interfaces.api.helpers import API_PREFIX

pytestmark = pytest.mark.django_db

# The properties parameter selects which properties of items a response returns (OGC API - Features - Part 6,
# Requirements Classes "Property Selection" and "Property Selection (Features)").

COLLECTIONS_PATH = "/api/ogc/collections"
FEATURE_COLLECTION_IDS = [collection.id for collection in COLLECTIONS if collection.item_type == "feature"]


@pytest.fixture(scope="module")
def openapi():
    return api.get_openapi_schema(path_prefix=API_PREFIX)


def _items_get_routes():
    """(collection id, OpenAPI path) for the items and item GET operations of every collection."""

    paths = api.get_openapi_schema(path_prefix=API_PREFIX)["paths"]
    for collection in COLLECTIONS:
        prefix = f"{API_PREFIX}collections/{collection.id}/items"
        for path, path_item in paths.items():
            is_items = path == prefix
            is_item = path.startswith(f"{prefix}/{{") and path.count("/") == prefix.count("/") + 1
            if (is_items or is_item) and "get" in path_item:
                yield collection.id, path


ITEMS_GET_ROUTES = list(_items_get_routes())


def _item_schema_fields(openapi, response_schema):
    """The properties of the items in a response document's data (a page or a single item)."""

    components = openapi["components"]["schemas"]

    def resolve(schema):
        return components[schema["$ref"].rsplit("/", 1)[-1]]

    document = resolve(response_schema["anyOf"][0] if "anyOf" in response_schema else response_schema)
    data = document["properties"]["data"]
    return set(resolve(data.get("items", data))["properties"])


@pytest.mark.parametrize("collection_id, path", ITEMS_GET_ROUTES, ids=[path for _, path in ITEMS_GET_ROUTES])
def test_properties_lists_every_returnable_property(openapi, collection_id, path):
    # Req 1B: the enum of the properties parameter lists the returnables, the properties of the response's items.
    operation = openapi["paths"][path]["get"]
    (parameter,) = [parameter for parameter in operation["parameters"] if parameter["name"] == "properties"]
    response_schema = operation["responses"][200]["content"]["application/json"]["schema"]

    assert (parameter["style"], parameter["explode"], parameter["schema"]["type"]) == ("form", False, "array")
    assert set(parameter["schema"]["items"]["enum"]) == _item_schema_fields(openapi, response_schema)


@pytest.mark.parametrize(
    "collection_id, property_name",
    [("etl-mappings", "etlTaskId"), ("data-product-transformations", "taskId"), ("monitoring-rules", "taskId")],
)
def test_properties_the_response_adds_to_its_fields_are_selectable(client, collection_id, property_name):
    client.force_login(UserFactory())

    response = client.get(f"{COLLECTIONS_PATH}/{collection_id}/items", {"properties": property_name})

    assert response.status_code == 200


@pytest.fixture
def features():
    """An item of each feature collection: an observation and the datastream, site and workspace it belongs to."""

    observation = ObservationFactory(
        datastream=DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    )
    datastream = observation.datastream
    site = datastream.monitoring_site
    return {"workspaces": site.workspace, "monitoring-sites": site, "datastreams": datastream, "observations": observation}


@pytest.mark.parametrize("collection_id", FEATURE_COLLECTION_IDS)
@pytest.mark.parametrize("item_route", [False, True], ids=["items", "item"])
def test_feature_collections_select_properties_of_items_and_an_item(client, features, collection_id, item_route):
    item = features[collection_id]
    path = f"{COLLECTIONS_PATH}/{collection_id}/items" + (f"/{item.id}" if item_route else "")

    data = client.get(path, {"properties": "id"}).json()["data"]
    feature = client.get(path, {"properties": "id", "f": "geojson"}).json()

    assert (data if item_route else data[0]) == {"id": str(item.id)}
    # GeoJSON keeps the members its media type requires, and the id isn't a feature property (Permission 1).
    assert (feature if item_route else feature["features"][0])["properties"] == {}
