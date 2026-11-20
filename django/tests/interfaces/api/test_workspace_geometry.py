import pytest

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import MonitoringSiteFactory

pytestmark = pytest.mark.django_db

# A workspace's GeoJSON geometry is the extent of the monitoring sites in it that the requester can view: a polygon
# with a bbox member, a point when those sites share one location, and no geometry without any. The bbox query
# parameter selects workspaces whose extent intersects the box (OGC API - Features Core Req 24).

WORKSPACES_PATH = "/api/ogc/collections/workspaces/items"


def _workspace(*locations, owner=None, private_locations=()):
    workspace = WorkspaceFactory(**({"owner": owner} if owner else {}))
    for longitude, latitude in locations:
        MonitoringSiteFactory(workspace=workspace, longitude=longitude, latitude=latitude)
    for longitude, latitude in private_locations:
        MonitoringSiteFactory(workspace=workspace, longitude=longitude, latitude=latitude, is_private=True)
    return workspace


def _feature(client, workspace):
    return client.get(f"{WORKSPACES_PATH}/{workspace.id}", {"f": "geojson"}).json()


def test_the_extent_of_a_workspaces_sites_is_a_polygon_with_a_bbox(client):
    workspace = _workspace((-112.0, 41.0), (-111.0, 42.5), (-111.5, 41.5))

    feature = _feature(client, workspace)

    assert feature["geometry"] == {
        "type": "Polygon",
        "coordinates": [[[-112.0, 41.0], [-111.0, 41.0], [-111.0, 42.5], [-112.0, 42.5], [-112.0, 41.0]]],
    }
    assert feature["bbox"] == [-112.0, 41.0, -111.0, 42.5]


def test_sites_at_one_location_give_a_point_without_a_bbox(client):
    workspace = _workspace((-111.8, 41.7), (-111.8, 41.7))

    feature = _feature(client, workspace)

    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}
    assert "bbox" not in feature


def test_a_workspace_without_sites_has_no_geometry(client):
    feature = _feature(client, _workspace())

    assert feature["geometry"] is None
    assert "bbox" not in feature


def test_the_extent_covers_only_the_sites_the_requester_can_view(client):
    owner = UserFactory()
    workspace = _workspace((-112.0, 41.0), owner=owner, private_locations=[(-110.0, 43.0)])

    anonymous = _feature(client, workspace)
    client.force_login(owner)
    owner_view = _feature(client, workspace)

    assert anonymous["geometry"] == {"type": "Point", "coordinates": [-112.0, 41.0]}
    assert owner_view["bbox"] == [-112.0, 41.0, -110.0, 43.0]


def test_a_page_of_workspaces_resolves_their_extents_in_one_query(client):
    for offset in range(3):
        _workspace((-112.0 + offset, 41.0), (-111.0 + offset, 42.0))

    with CaptureQueriesContext(connection) as json_queries:
        client.get(WORKSPACES_PATH)
    with CaptureQueriesContext(connection) as geojson_queries:
        features = client.get(WORKSPACES_PATH, {"f": "geojson"}).json()["features"]

    assert len(geojson_queries) == len(json_queries) + 1
    assert all(feature["geometry"]["type"] == "Polygon" for feature in features)


@pytest.mark.parametrize(
    "bbox, matches",
    [
        ("-111.6,41.4,-111.4,41.6", True),  # inside the extent, where the workspace has no site
        ("-111.1,42.4,-110.0,43.0", True),  # overlapping a corner of the extent
        ("-120.0,30.0,-100.0,50.0", True),  # containing the whole extent
        ("-110.0,41.0,-109.0,42.0", False),  # east of the extent
        ("-112.0,43.0,-111.0,44.0", False),  # north of the extent
        ("170,40,-111.5,43", True),  # crossing the antimeridian and reaching the extent from the east
        ("170,40,-115,43", False),  # crossing the antimeridian, short of the extent
    ],
)
def test_bbox_selects_workspaces_whose_extent_intersects_the_box(client, bbox, matches):
    workspace = _workspace((-112.0, 41.0), (-111.0, 42.5))

    ids = [item["id"] for item in client.get(WORKSPACES_PATH, {"bbox": bbox}).json()["data"]]

    assert (str(workspace.id) in ids) is matches


def test_bbox_ignores_sites_the_requester_cant_view(client):
    workspace = _workspace((-112.0, 41.0), private_locations=[(-100.0, 41.0)])

    ids = [item["id"] for item in client.get(WORKSPACES_PATH, {"bbox": "-101,40,-99,42"}).json()["data"]]

    assert str(workspace.id) not in ids


def test_workspaces_without_visible_sites_match_any_bbox(client):
    workspace = _workspace(private_locations=[(-112.0, 41.0)])

    ids = [item["id"] for item in client.get(WORKSPACES_PATH, {"bbox": "0,0,1,1"}).json()["data"]]

    assert str(workspace.id) in ids


def test_feature_geometry_is_documented_as_a_point_or_polygon_with_an_optional_bbox(client):
    components = client.get("/api/ogc/openapi.json").json()["components"]["schemas"]
    feature = components["GeoJSONFeatureDocument_WorkspaceProperties_"]["properties"]

    geometry = feature["geometry"]["anyOf"][0]
    assert {option["$ref"].rsplit("/", 1)[-1] for option in geometry["oneOf"]} == {"GeoJSONPoint", "GeoJSONPolygon"}
    assert feature["bbox"]["anyOf"][0]["minItems"] == feature["bbox"]["anyOf"][0]["maxItems"] == 4
