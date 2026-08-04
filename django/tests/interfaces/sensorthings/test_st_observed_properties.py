import pytest

from tests.core.sta.factories import ObservedPropertyFactory

pytestmark = pytest.mark.django_db

OBSERVED_PROPERTIES_URL = "/api/sensorthings/v1.1/ObservedProperties"


def _detail_url(observed_property_id):
    return f"{OBSERVED_PROPERTIES_URL}('{observed_property_id}')"


def test_get_observed_properties_collection_returns_200(client):
    observed_property = ObservedPropertyFactory()

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert str(observed_property.id) in [
        op["@iot.id"] for op in response.json()["value"]
    ]


def test_get_observed_property_returns_200(client):
    observed_property = ObservedPropertyFactory()

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(observed_property.id)
