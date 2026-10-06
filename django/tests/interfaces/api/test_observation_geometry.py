import pytest

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.core.iam.factories import CollaboratorFactory, PermissionFactory, RoleFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory

pytestmark = pytest.mark.django_db

# An observation's GeoJSON geometry is the location of its datastream's monitoring site, or no geometry when the
# requester can't view that site. The bbox query parameter selects observations by that geometry (OGC API -
# Features Core Req 24).

OBSERVATIONS_PATH = "/api/ogc/collections/observations/items"


def _observation(longitude=-111.8, latitude=41.7, site=None, workspace=None):
    site = site or MonitoringSiteFactory(
        longitude=longitude, latitude=latitude, **({"workspace": workspace} if workspace else {})
    )
    return ObservationFactory(datastream=DatastreamFactory(monitoring_site=site))


def _feature(client, observation, **params):
    return client.get(f"{OBSERVATIONS_PATH}/{observation.id}", {"f": "geojson", **params}).json()


def _ids(client, bbox):
    return [item["id"] for item in client.get(OBSERVATIONS_PATH, {"bbox": bbox}).json()["data"]]


def test_an_observations_geometry_is_its_datastreams_site_location(client):
    observation = _observation(-111.8, 41.7)

    feature = _feature(client, observation)

    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}
    assert "bbox" not in feature
    assert feature["properties"]["datastreamId"] == str(observation.datastream_id)


def test_a_page_of_observations_resolves_their_sites_locations_in_one_query(client):
    shared_site = MonitoringSiteFactory(longitude=-112.0, latitude=41.0)
    longitudes = {
        str(_observation(site=shared_site).id): -112.0,
        str(_observation(site=shared_site).id): -112.0,
        str(_observation(-110.0, 41.0).id): -110.0,
    }

    with CaptureQueriesContext(connection) as json_queries:
        client.get(OBSERVATIONS_PATH)
    with CaptureQueriesContext(connection) as geojson_queries:
        features = client.get(OBSERVATIONS_PATH, {"f": "geojson"}).json()["features"]

    assert len(geojson_queries) == len(json_queries) + 1
    assert {feature["id"]: feature["geometry"]["coordinates"][0] for feature in features} == longitudes


def test_the_datastream_reference_is_left_out_of_properties_that_dont_select_it(client):
    observation = _observation(-111.8, 41.7)

    feature = _feature(client, observation, properties="result")

    assert feature["properties"] == {"result": observation.result}
    assert feature["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}


def test_the_datastream_reference_is_kept_in_properties_that_select_it(client):
    observation = _observation()

    feature = _feature(client, observation, properties="result,datastreamId")

    assert feature["properties"] == {"result": observation.result, "datastreamId": str(observation.datastream_id)}


@pytest.fixture
def hidden_site(client):
    """An observation in a private workspace whose collaborator can view observations but not monitoring sites."""

    workspace = WorkspaceFactory(private=True)
    role = RoleFactory(workspace=workspace)
    for resource_type in ("Workspace", "Datastream", "Observation"):
        PermissionFactory(role=role, resource_type=resource_type, can_view=True)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)
    client.force_login(collaborator.user)
    return _observation(-111.8, 41.7, workspace=workspace)


def test_observations_whose_site_the_requester_cant_view_have_no_geometry(client, hidden_site):
    assert _feature(client, hidden_site)["geometry"] is None


def test_observations_whose_site_the_requester_cant_view_match_any_bbox(client, hidden_site):
    assert str(hidden_site.id) in _ids(client, "0,0,1,1")


def test_the_owner_sees_the_site_location_and_bbox_filters_by_it(client, hidden_site):
    client.force_login(hidden_site.datastream.monitoring_site.workspace.owner)

    assert _feature(client, hidden_site)["geometry"] == {"type": "Point", "coordinates": [-111.8, 41.7]}
    assert str(hidden_site.id) not in _ids(client, "0,0,1,1")
    assert str(hidden_site.id) in _ids(client, "-112,41,-111,42")
