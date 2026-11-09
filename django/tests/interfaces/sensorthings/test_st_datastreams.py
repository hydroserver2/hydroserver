import json
from datetime import timedelta

import pytest
from django.utils import timezone

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from interfaces.sensorthings.adapter.utils import OM_MEASUREMENT
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory

pytestmark = pytest.mark.django_db

DATASTREAMS_URL = "/api/sensorthings/v1.1/Datastreams"


def _detail_url(datastream_id):
    return f"{DATASTREAMS_URL}('{datastream_id}')"


def test_get_datastreams_collection_returns_200(client):
    datastream = DatastreamFactory()

    response = client.get(DATASTREAMS_URL)

    assert response.status_code == 200
    assert str(datastream.id) in [d["@iot.id"] for d in response.json()["value"]]


def test_get_datastream_returns_200(client):
    datastream = DatastreamFactory()

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(datastream.id)


def test_get_datastream_with_unit_without_definition_returns_200(client):
    datastream = DatastreamFactory(unit__definition=None)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["unitOfMeasurement"]["definition"] == ""


def test_get_datastream_includes_tags_in_properties(client):
    datastream = DatastreamFactory(tags={"season": "summer"})

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["properties"]["tags"] == {"season": "summer"}


def test_get_datastream_returns_empty_tags_when_untagged(client):
    datastream = DatastreamFactory()

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["properties"]["tags"] == {}


@pytest.mark.parametrize(
    "query, matches",
    [
        (f"observationType eq '{OM_MEASUREMENT}'", True),
        ("observationType eq 'OM_Measurement'", False),
        ("properties/type eq 'timeSeriesCoverage'", True),
        ("properties/type eq 'profileCoverage'", False),
    ],
)
def test_get_datastreams_filters_by_observation_type_and_type(client, query, matches):
    datastream = DatastreamFactory()

    response = client.get(DATASTREAMS_URL, {"$filter": query, "$orderby": "observationType"})

    assert response.status_code == 200
    ids = [d["@iot.id"] for d in response.json()["value"]]
    assert (str(datastream.id) in ids) is matches
