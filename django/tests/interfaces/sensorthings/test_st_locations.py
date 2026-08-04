import pytest

from tests.core.sta.factories import LocationFactory, ThingFactory

pytestmark = pytest.mark.django_db

LOCATIONS_URL = "/api/sensorthings/v1.1/Locations"


def _detail_url(location_id):
    return f"{LOCATIONS_URL}('{location_id}')"


def test_get_locations_collection_returns_200(client):
    location = LocationFactory(thing=ThingFactory())

    response = client.get(LOCATIONS_URL)

    assert response.status_code == 200
    assert str(location.id) in [loc["@iot.id"] for loc in response.json()["value"]]


def test_get_location_returns_200(client):
    location = LocationFactory(thing=ThingFactory())

    response = client.get(_detail_url(location.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(location.id)
