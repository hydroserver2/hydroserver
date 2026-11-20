import pytest

from tests.core.sta.factories import MonitoringSiteFactory

pytestmark = pytest.mark.django_db

LOCATIONS_URL = "/api/sensorthings/v1.1/Locations"


def _detail_url(location_id):
    return f"{LOCATIONS_URL}('{location_id}')"


def test_get_locations_collection_returns_200(client):
    site = MonitoringSiteFactory()

    response = client.get(LOCATIONS_URL)

    assert response.status_code == 200
    assert str(site.id) in [loc["@iot.id"] for loc in response.json()["value"]]


def test_get_location_returns_200(client):
    site = MonitoringSiteFactory()

    response = client.get(_detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(site.id)
