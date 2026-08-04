import pytest

from tests.core.sta.factories import ThingFactory

pytestmark = pytest.mark.django_db

THINGS_URL = "/api/sensorthings/v1.1/Things"


def _detail_url(thing_id):
    return f"{THINGS_URL}('{thing_id}')"


def test_get_things_collection_returns_200(client):
    thing = ThingFactory()

    response = client.get(THINGS_URL)

    assert response.status_code == 200
    assert str(thing.id) in [t["@iot.id"] for t in response.json()["value"]]


def test_get_thing_returns_200(client):
    thing = ThingFactory()

    response = client.get(_detail_url(thing.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(thing.id)
