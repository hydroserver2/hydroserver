import pytest

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.core.iam.factories import CollaboratorFactory, PermissionFactory, RoleFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory

pytestmark = pytest.mark.django_db

# A datastream's GeoJSON geometry is the location of its monitoring site, or no geometry when the requester can't
# view that site. The bbox query parameter selects datastreams by that geometry (OGC API - Features Core Req 24).

DATASTREAMS_PATH = "/api/ogc/collections/datastreams/items"


def _datastream(longitude=-111.8, latitude=41.7, workspace=None):
    site = MonitoringSiteFactory(
        longitude=longitude, latitude=latitude, **({"workspace": workspace} if workspace else {})
    )
    return DatastreamFactory(monitoring_site=site)


def _feature(client, datastream, **params):
    return client.get(f"{DATASTREAMS_PATH}/{datastream.id}", {"f": "geojson", **params}).json()


def _ids(client, bbox):
    return [item["id"] for item in client.get(DATASTREAMS_PATH, {"bbox": bbox}).json()["data"]]


def test_a_datastreams_geometry_is_its_sites_location(client):
    datastream = _datastream(-111.8, 41.7)

    feature = _feature(client, datastream)

    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}
    assert "bbox" not in feature
    assert feature["properties"]["monitoringSiteId"] == str(datastream.monitoring_site_id)


def test_a_page_of_datastreams_resolves_their_sites_locations_in_one_query(client):
    datastreams = {str(_datastream(-112.0 + offset, 41.0).id): -112.0 + offset for offset in range(3)}

    with CaptureQueriesContext(connection) as json_queries:
        client.get(DATASTREAMS_PATH)
    with CaptureQueriesContext(connection) as geojson_queries:
        features = client.get(DATASTREAMS_PATH, {"f": "geojson"}).json()["features"]

    assert len(geojson_queries) == len(json_queries) + 1
    assert {feature["id"]: feature["geometry"]["coordinates"][0] for feature in features} == datastreams


def test_the_site_reference_is_left_out_of_properties_that_dont_select_it(client):
    datastream = _datastream(-111.8, 41.7)

    feature = _feature(client, datastream, properties="name")

    assert feature["properties"] == {"name": datastream.name}
    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}


def test_the_site_reference_is_kept_in_properties_that_select_it(client):
    datastream = _datastream()

    feature = _feature(client, datastream, properties="name,monitoringSiteId")

    assert feature["properties"] == {"name": datastream.name, "monitoringSiteId": str(datastream.monitoring_site_id)}


@pytest.fixture
def hidden_site(client):
    """A datastream in a private workspace whose collaborator can view datastreams but not monitoring sites."""

    workspace = WorkspaceFactory(private=True)
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Workspace", can_view=True)
    PermissionFactory(role=role, resource_type="Datastream", can_view=True)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)
    client.force_login(collaborator.user)
    return _datastream(-111.8, 41.7, workspace=workspace)


def test_datastreams_whose_site_the_requester_cant_view_have_no_geometry(client, hidden_site):
    assert _feature(client, hidden_site)["geometry"] is None


def test_datastreams_whose_site_the_requester_cant_view_match_any_bbox(client, hidden_site):
    assert str(hidden_site.id) in _ids(client, "0,0,1,1")


def test_the_owner_sees_the_site_location_and_bbox_filters_by_it(client, hidden_site):
    client.force_login(hidden_site.monitoring_site.workspace.owner)

    assert _feature(client, hidden_site)["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}
    assert str(hidden_site.id) not in _ids(client, "0,0,1,1")
    assert str(hidden_site.id) in _ids(client, "-112,41,-111,42")
