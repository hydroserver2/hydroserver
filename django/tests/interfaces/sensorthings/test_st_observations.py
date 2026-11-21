from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest
from django.utils import timezone

from core.sta.models import Observation

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, ObservationFactory, MonitoringSiteFactory

pytestmark = pytest.mark.django_db

OBSERVATIONS_URL = "/api/sensorthings/v1.1/Observations"
CREATE_OBSERVATIONS_URL = "/api/sensorthings/v1.1/CreateObservations"


def _detail_url(observation_id):
    return f"{OBSERVATIONS_URL}('{observation_id}')"


def _iso(dt):
    return dt.astimezone(dt_timezone.utc).isoformat()


# --- get_observations ------------------------------------------------------------------


def test_get_observations_collection_returns_200(client):
    observation = ObservationFactory()

    response = client.get(OBSERVATIONS_URL)

    assert response.status_code == 200
    assert str(observation.id) in [o["@iot.id"] for o in response.json()["value"]]


def test_get_observation_returns_200(client):
    observation = ObservationFactory()

    response = client.get(_detail_url(observation.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(observation.id)


# --- restricted datastreams --------------------------------------------------------------


def _restricted_and_open_observations(owner=None):
    workspace = WorkspaceFactory(owner=owner) if owner else WorkspaceFactory()
    restricted = DatastreamFactory(
        monitoring_site=MonitoringSiteFactory(workspace=workspace), restricted=True, value_count=1
    )
    open_ = DatastreamFactory(
        monitoring_site=MonitoringSiteFactory(workspace=workspace), value_count=1
    )
    return ObservationFactory(datastream=restricted), ObservationFactory(datastream=open_)


def test_get_observations_excludes_restricted_datastream_observations_for_anonymous(client):
    restricted_observation, open_observation = _restricted_and_open_observations()

    response = client.get(f"{OBSERVATIONS_URL}?$count=true")

    assert response.status_code == 200
    ids = [o["@iot.id"] for o in response.json()["value"]]
    assert str(open_observation.id) in ids
    assert str(restricted_observation.id) not in ids
    assert response.json()["@iot.count"] == 1


def test_get_observations_includes_restricted_datastream_observations_for_owner(client):
    owner = UserFactory()
    restricted_observation, open_observation = _restricted_and_open_observations(owner)
    client.force_login(owner)

    response = client.get(f"{OBSERVATIONS_URL}?$count=true")

    assert response.status_code == 200
    ids = [o["@iot.id"] for o in response.json()["value"]]
    assert str(open_observation.id) in ids
    assert str(restricted_observation.id) in ids
    assert response.json()["@iot.count"] == 2


def test_get_observation_returns_404_for_restricted_datastream_observation_when_anonymous(client):
    restricted_observation, _ = _restricted_and_open_observations()

    response = client.get(_detail_url(restricted_observation.id))

    assert response.status_code == 404


# --- create_observation_entity (POST /Observations) -------------------------------------


def _observation_post_body(datastream_id, **overrides):
    body = {
        "phenomenonTime": _iso(timezone.now()),
        "result": 1.23,
        "Datastream": {"@iot.id": str(datastream_id)},
    }
    body.update(overrides)
    return body


def test_post_observation_returns_403_for_anonymous(client):
    workspace = WorkspaceFactory()
    thing = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=thing)

    response = client.post(
        OBSERVATIONS_URL,
        data=_observation_post_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_post_observation_returns_404_for_private_datastream_when_anonymous(client):
    workspace = WorkspaceFactory(is_private=True)
    thing = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=thing)

    response = client.post(
        OBSERVATIONS_URL,
        data=_observation_post_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_post_observation_succeeds_for_authenticated_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=thing)
    client.force_login(owner)

    response = client.post(
        OBSERVATIONS_URL,
        data=_observation_post_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201


# --- create_observation_entities (POST /CreateObservations) ------------------------------


def _create_observations_body(datastream_id, **overrides):
    body = [
        {
            "Datastream": {"@iot.id": str(datastream_id)},
            "components": ["phenomenonTime", "result"],
            "dataArray": [[_iso(timezone.now()), 1.23]],
        }
    ]
    if overrides:
        body[0].update(overrides)
    return body


def test_create_observations_returns_error_marker_for_anonymous(client):
    workspace = WorkspaceFactory()
    thing = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=thing)

    response = client.post(
        CREATE_OBSERVATIONS_URL,
        data=_create_observations_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json() == ["error"]


def test_create_observations_succeeds_for_authenticated_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=thing)
    client.force_login(owner)

    response = client.post(
        CREATE_OBSERVATIONS_URL,
        data=_create_observations_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201


# --- profile coverage datastreams --------------------------------------------------------


def _profile_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), profile=True)


def test_post_observation_stores_parameters_z_on_profile(client):
    datastream = _profile_datastream(client)

    response = client.post(
        OBSERVATIONS_URL,
        data=_observation_post_body(datastream.id, parameters={"z": 2.5}),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert Observation.objects.get(datastream=datastream).z == Decimal("2.5")
    datastream.refresh_from_db()
    assert (datastream.z_min, datastream.z_max) == (Decimal("2.5"), Decimal("2.5"))


def test_post_observation_returns_400_without_z_on_profile(client):
    datastream = _profile_datastream(client)

    response = client.post(
        OBSERVATIONS_URL,
        data=_observation_post_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not Observation.objects.exists()


def test_get_observation_returns_parameters_z_on_profile(client):
    datastream = _profile_datastream(client)
    observation = ObservationFactory(datastream=datastream, z=Decimal("2.5"))

    response = client.get(_detail_url(observation.id))

    assert response.json()["parameters"] == {"z": 2.5}
