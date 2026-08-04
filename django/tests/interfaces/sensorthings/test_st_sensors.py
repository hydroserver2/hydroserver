import pytest

from tests.core.sta.factories import SensorFactory

pytestmark = pytest.mark.django_db

SENSORS_URL = "/api/sensorthings/v1.1/Sensors"


def _detail_url(sensor_id):
    return f"{SENSORS_URL}('{sensor_id}')"


def test_get_sensors_collection_returns_200(client):
    sensor = SensorFactory()

    response = client.get(SENSORS_URL)

    assert response.status_code == 200
    assert str(sensor.id) in [s["@iot.id"] for s in response.json()["value"]]


def test_get_sensor_returns_200(client):
    sensor = SensorFactory()

    response = client.get(_detail_url(sensor.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(sensor.id)
