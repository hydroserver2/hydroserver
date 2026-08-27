import pytest

from tests.core.sta.factories import DatastreamFactory

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
