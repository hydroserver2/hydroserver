import pytest

pytestmark = pytest.mark.django_db

HISTORICAL_LOCATIONS_URL = "/api/sensorthings/v1.1/HistoricalLocations"


def test_get_historical_locations_collection_returns_empty(client):
    response = client.get(HISTORICAL_LOCATIONS_URL)

    assert response.status_code == 200
    assert response.json()["value"] == []
