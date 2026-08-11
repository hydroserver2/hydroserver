import pytest

from tests.core.sta.factories import MethodFactory

pytestmark = pytest.mark.django_db

SENSORS_URL = "/api/sensorthings/v1.1/Sensors"


def _detail_url(sensor_id):
    return f"{SENSORS_URL}('{sensor_id}')"


def test_get_sensors_collection_returns_200(client):
    method = MethodFactory()

    response = client.get(SENSORS_URL)

    assert response.status_code == 200
    assert str(method.id) in [sensor["@iot.id"] for sensor in response.json()["value"]]


def test_get_sensor_returns_200(client):
    method = MethodFactory()

    response = client.get(_detail_url(method.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(method.id)
