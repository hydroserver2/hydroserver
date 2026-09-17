from datetime import timezone as dt_timezone

import pytest
from django.utils import timezone

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
