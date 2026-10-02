from urllib.parse import parse_qs, urlsplit

import pytest

from pydantic import ValidationError

from interfaces.api.collections import COLLECTIONS, get_collection
from interfaces.api.formats.geojson.features import feature_collection_schema, feature_properties_schema, feature_schema
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory

pytestmark = pytest.mark.django_db

# Feature collections serve their items as GeoJSON (OGC API - Features Core Req 38-39): a FeatureCollection for
# items and a Feature for an item, with the item id as the feature id, the geometry fields as a 2D point, and
# links and included resources as foreign members.

COLLECTIONS_PATH = "/api/ogc/collections"
GEOJSON = "application/geo+json"
FEATURE_COLLECTION_IDS = ["workspaces", "monitoring-sites", "datastreams", "observations"]
GEOJSON_CONFORMANCE = "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson"


def _items_path(collection_id):
    return f"{COLLECTIONS_PATH}/{collection_id}/items"


@pytest.fixture
def observation():
    site = MonitoringSiteFactory(workspace=WorkspaceFactory(), latitude=41.7, longitude=-111.8, elevation_m=1400.0)
    return ObservationFactory(datastream=DatastreamFactory(monitoring_site=site))


def _items(observation):
    """The item of each feature collection that the observation belongs to."""

    datastream = observation.datastream
    site = datastream.monitoring_site
    return {
        "workspaces": site.workspace,
        "monitoring-sites": site,
        "datastreams": datastream,
        "observations": observation,
    }


def _get_geojson(client, path, **params):
    return client.get(path, {"f": "geojson", **params})


def test_items_are_a_feature_collection(client, observation):
    site = observation.datastream.monitoring_site

    response = _get_geojson(client, _items_path("monitoring-sites"))
    json_body = client.get(_items_path("monitoring-sites")).json()

    assert response.status_code == 200
    assert response["Content-Type"] == f"{GEOJSON}; charset=utf-8"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["numberMatched"] == json_body["meta"]["numberMatched"]
    assert body["numberReturned"] == len(body["features"]) == len(json_body["data"])
    (feature,) = body["features"]
    assert feature["type"] == "Feature"
    assert feature["id"] == str(site.id)
    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}


def test_feature_properties_leave_out_the_id_and_geometry_fields(client, observation):
    (feature,) = _get_geojson(client, _items_path("monitoring-sites")).json()["features"]

    assert {"id", "latitude", "longitude"}.isdisjoint(feature["properties"])
    assert feature["properties"]["elevation_m"] == 1400.0
    assert feature["properties"]["name"] == observation.datastream.monitoring_site.name


def test_item_is_a_feature_with_the_path_id(client, observation):
    site = observation.datastream.monitoring_site

    response = _get_geojson(client, f"{_items_path('monitoring-sites')}/{site.id}")

    body = response.json()
    assert body["type"] == "Feature"
    assert body["id"] == str(site.id)
    assert body["geometry"]["type"] == "Point"
    assert {link["rel"] for link in body["links"]} == {"self", "alternate", "collection"}


@pytest.mark.parametrize("collection_id", ["datastreams", "observations"])
def test_features_without_a_geometry_have_null_geometry(client, observation, collection_id):
    item = _items(observation)[collection_id]

    response = _get_geojson(client, f"{_items_path(collection_id)}/{item.id}")

    assert response.json()["geometry"] is None
    assert response.json()["id"] == str(item.id)


@pytest.mark.parametrize("collection_id", FEATURE_COLLECTION_IDS)
def test_responses_match_their_documented_models(client, observation, collection_id):
    collection = get_collection(collection_id)
    item = _items(observation)[collection_id]

    items_body = _get_geojson(client, _items_path(collection_id)).json()
    item_body = _get_geojson(client, f"{_items_path(collection_id)}/{item.id}").json()

    feature_collection_schema(collection).model_validate(items_body)
    feature_schema(collection).model_validate(item_body)
    assert "id" not in feature_properties_schema(collection).model_fields


def test_accept_header_selects_geojson_and_links_carry_f(client, observation):
    MonitoringSiteFactory(workspace=observation.datastream.monitoring_site.workspace)

    response = client.get(_items_path("monitoring-sites"), {"limit": 1}, headers={"Accept": GEOJSON})

    links = {link["rel"]: link for link in response.json()["links"]}
    for rel in ("self", "next"):
        assert links[rel]["type"] == GEOJSON
        assert parse_qs(urlsplit(links[rel]["href"]).query)["f"] == ["geojson"]
    assert links["alternate"]["type"] == "application/json"


def test_included_resources_are_a_foreign_member(client, observation):
    response = _get_geojson(client, _items_path("observations"), include="datastream")

    assert [datastream["id"] for datastream in response.json()["included"]["datastreams"]] == [
        str(observation.datastream.id)
    ]


def test_properties_parameter_selects_properties_but_keeps_id_and_geometry(client, observation):
    site = observation.datastream.monitoring_site

    (named,) = _get_geojson(client, _items_path("monitoring-sites"), properties="name").json()["features"]
    (located,) = _get_geojson(client, _items_path("monitoring-sites"), properties="latitude").json()["features"]

    assert named["id"] == str(site.id)
    assert named["geometry"]["coordinates"] == [-111.8, 41.7]
    assert named["properties"] == {"name": site.name}
    assert located["properties"] == {}
    assert located["geometry"]["coordinates"] == [-111.8, 41.7]
    assert client.get(_items_path("monitoring-sites"), {"properties": "name"}).json()["data"] == [{"name": site.name}]


@pytest.mark.parametrize("profile", ["https://hydroserver.org/profiles/observations/row", "https://hydroserver.org/profiles/observations/column"])
def test_observation_row_and_column_profiles_do_not_apply_to_geojson(client, observation, profile):
    response = _get_geojson(
        client, _items_path("observations"), profile=profile, datastream_id=str(observation.datastream.id)
    )

    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert [feature["id"] for feature in body["features"]] == [str(observation.id)]


def test_resource_collections_do_not_serve_geojson(client):
    assert _get_geojson(client, _items_path("units")).status_code == 400
    assert client.get(_items_path("units"), headers={"Accept": GEOJSON}).status_code == 406


def test_feature_collections_are_the_geojson_collections():
    # Req 38: resources with feature content are served as GeoJSON.
    for collection in COLLECTIONS:
        serves_geojson = "geojson" in collection.formats
        assert serves_geojson == (collection.item_type == "feature"), collection.id
        assert (collection.feature is not None) == serves_geojson, collection.id


def test_conformance_declares_geojson(client):
    assert GEOJSON_CONFORMANCE in client.get("/api/ogc/conformance").json()["conformsTo"]


def test_openapi_documents_geojson_responses(client):
    schema = client.get("/api/ogc/openapi.json").json()
    paths, components = schema["paths"], schema["components"]["schemas"]

    for path, path_item in paths.items():
        if not path.endswith(("/monitoring-sites/items", "/monitoring-sites/items/{monitoring_site_id}")):
            continue
        get = path_item["get"]
        content = get["responses"]["200"]["content"]
        assert set(content) == {"application/json", GEOJSON}
        assert content[GEOJSON]["schema"]["$ref"].removeprefix("#/components/schemas/") in components
        (f,) = [param for param in get["parameters"] if param["name"] == "f"]
        assert f["schema"]["enum"] == ["json", "geojson"]

    properties = components["MonitoringSiteProperties"]["properties"]
    assert {"id", "latitude", "longitude"}.isdisjoint(properties)
    assert "elevation_m" in properties

    units_get = next(item["get"] for path, item in paths.items() if path.endswith("/units/items"))
    assert set(units_get["responses"]["200"]["content"]) == {"application/json"}


def _resolve(components, schema):
    return components[schema["$ref"].removeprefix("#/components/schemas/")]


def test_openapi_documents_links_and_included_on_documents_not_features(client):
    schema = client.get("/api/ogc/openapi.json").json()
    paths, components = schema["paths"], schema["components"]["schemas"]

    def geojson_schema(suffix):
        path = next(path for path in paths if path.endswith(suffix))
        return _resolve(components, paths[path]["get"]["responses"]["200"]["content"][GEOJSON]["schema"])

    feature_collection = geojson_schema("/monitoring-sites/items")
    feature = _resolve(components, feature_collection["properties"]["features"]["items"])
    feature_document = geojson_schema("/monitoring-sites/items/{monitoring_site_id}")

    assert {"links", "included"} <= set(feature_collection["properties"])
    assert {"links", "included"}.isdisjoint(feature["properties"])
    assert {"links", "included"} <= set(feature_document["properties"])
    assert "links" in feature_document["required"]


def test_documented_models_reject_members_the_documentation_lacks(client, observation):
    collection = get_collection("monitoring-sites")
    body = _get_geojson(client, _items_path("monitoring-sites")).json()
    body["features"][0]["links"] = body["links"]

    with pytest.raises(ValidationError):
        feature_collection_schema(collection).model_validate(body)


@pytest.mark.parametrize("collection_id", FEATURE_COLLECTION_IDS)
def test_json_items_are_their_properties_plus_id_and_geometry_fields(client, observation, collection_id):
    collection = get_collection(collection_id)
    properties = feature_properties_schema(collection).model_json_schema(mode="serialization", by_alias=True)
    geometry = set(collection.feature.geometry.fields) if collection.feature.geometry else set()
    item = _items(observation)[collection_id]

    json_item = client.get(f"{_items_path(collection_id)}/{item.id}").json()["data"]

    assert {"id", *geometry}.isdisjoint(properties["properties"])
    assert set(json_item) == {*properties["properties"], "id", *geometry}
