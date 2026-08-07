import pytest

from tests.core.sta.factories import MonitoringSiteFactory

pytestmark = pytest.mark.django_db

FEATURES_OF_INTEREST_URL = "/api/sensorthings/v1.1/FeaturesOfInterest"


def test_get_features_of_interest_collection_returns_monitoring_sites(client):
    site = MonitoringSiteFactory()

    response = client.get(FEATURES_OF_INTEREST_URL)

    assert response.status_code == 200
    feature = response.json()["value"][0]
    assert feature["@iot.id"] == str(site.id)
    assert feature["name"] == site.name
    assert feature["feature"]["geometry"]["coordinates"] == [
        site.longitude,
        site.latitude,
    ]
