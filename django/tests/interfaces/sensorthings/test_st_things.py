import pytest

from tests.core.sta.factories import MonitoringSiteFactory

pytestmark = pytest.mark.django_db

THINGS_URL = "/api/sensorthings/v1.1/Things"


def _detail_url(thing_id):
    return f"{THINGS_URL}('{thing_id}')"


def test_get_things_collection_returns_200(client):
    site = MonitoringSiteFactory()

    response = client.get(THINGS_URL)

    assert response.status_code == 200
    assert str(site.id) in [thing["@iot.id"] for thing in response.json()["value"]]


def test_get_thing_returns_200(client):
    site = MonitoringSiteFactory()

    response = client.get(_detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["@iot.id"] == str(site.id)


def test_get_thing_includes_tags_in_properties(client):
    site = MonitoringSiteFactory(tags={"basin": "logan-river"})

    response = client.get(_detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["properties"]["tags"] == {"basin": "logan-river"}


def test_get_thing_returns_empty_tags_when_untagged(client):
    site = MonitoringSiteFactory()

    response = client.get(_detail_url(site.id))

    assert response.status_code == 200
    assert response.json()["properties"]["tags"] == {}
