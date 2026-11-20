import pytest

pytestmark = pytest.mark.django_db

FEATURES_OF_INTEREST_URL = "/api/sensorthings/v1.1/FeaturesOfInterest"


def test_get_features_of_interest_collection_returns_empty(client):
    response = client.get(FEATURES_OF_INTEREST_URL)

    assert response.status_code == 200
    assert response.json()["value"] == []
