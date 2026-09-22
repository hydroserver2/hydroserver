import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import DatastreamStatusFactory

pytestmark = pytest.mark.django_db

DATASTREAM_STATUSES_URL = "/api/data/datastream-statuses"


def _detail_url(datastream_status_id):
    return f"{DATASTREAM_STATUSES_URL}/{datastream_status_id}"


def _datastream_status_body(**overrides):
    body = {
        "name": "New Status",
        "description": "A new datastream status.",
    }
    body.update(overrides)
    return body


# --- get_datastream_statuses --------------------------------------------------------------


def test_get_datastream_statuses_visible_to_anonymous(client):
    datastream_status = DatastreamStatusFactory()

    response = client.get(DATASTREAM_STATUSES_URL)

    assert response.status_code == 200
    assert str(datastream_status.id) in [r["id"] for r in response.json()["data"]]


def test_get_datastream_statuses_visible_to_any_authenticated_user(client):
    datastream_status = DatastreamStatusFactory()
    client.force_login(UserFactory())

    response = client.get(DATASTREAM_STATUSES_URL)

    assert response.status_code == 200
    assert str(datastream_status.id) in [r["id"] for r in response.json()["data"]]


def test_get_datastream_statuses_properties_filters_every_item_in_the_list(client):
    DatastreamStatusFactory(name="A")
    DatastreamStatusFactory(name="B")

    response = client.get(DATASTREAM_STATUSES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_datastream_statuses_properties_rejects_unknown_property(client):
    response = client.get(DATASTREAM_STATUSES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_datastream_statuses_without_properties_returns_every_field(client):
    DatastreamStatusFactory(name="A")

    response = client.get(DATASTREAM_STATUSES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_datastream_statuses_q_searches_name_and_description(client):
    DatastreamStatusFactory(name="Alpha term", description="")
    DatastreamStatusFactory(name="Beta term", description="")

    response = client.get(DATASTREAM_STATUSES_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_datastream_statuses_sortby_name_descending(client):
    DatastreamStatusFactory(name="Alpha")
    DatastreamStatusFactory(name="Beta")

    response = client.get(DATASTREAM_STATUSES_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_datastream_status ------------------------------------------------------------


def test_create_datastream_status_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        DATASTREAM_STATUSES_URL,
        data=_datastream_status_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    datastream_status_id = response.json()["id"]

    detail = client.get(_detail_url(datastream_status_id))
    assert detail.json()["data"]["name"] == "New Status"


def test_create_datastream_status_returns_401_when_unauthenticated(client):
    response = client.post(
        DATASTREAM_STATUSES_URL,
        data=_datastream_status_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_datastream_status_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        DATASTREAM_STATUSES_URL,
        data=_datastream_status_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_datastream_status_returns_400_for_duplicate_name(client):
    DatastreamStatusFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        DATASTREAM_STATUSES_URL,
        data=_datastream_status_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_datastream_status ----------------------------------------------------------------


def test_get_datastream_status_returns_200_for_anonymous(client):
    datastream_status = DatastreamStatusFactory()

    response = client.get(_detail_url(datastream_status.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(datastream_status.id)


def test_get_datastream_status_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_datastream_status_properties_rejects_unknown_property(client):
    datastream_status = DatastreamStatusFactory()

    response = client.get(_detail_url(datastream_status.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_datastream_status -------------------------------------------------------------


def test_update_datastream_status_succeeds_for_superuser(client):
    datastream_status = DatastreamStatusFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(datastream_status.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(datastream_status.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_datastream_status_returns_401_when_unauthenticated(client):
    datastream_status = DatastreamStatusFactory()

    response = client.patch(
        _detail_url(datastream_status.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_datastream_status_returns_403_for_non_superuser(client):
    datastream_status = DatastreamStatusFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(datastream_status.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_datastream_status -------------------------------------------------------------


def test_delete_datastream_status_succeeds_for_superuser(client):
    datastream_status = DatastreamStatusFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(datastream_status.id))

    assert response.status_code == 204
    assert client.get(_detail_url(datastream_status.id)).status_code == 404


def test_delete_datastream_status_returns_403_for_non_superuser(client):
    datastream_status = DatastreamStatusFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(datastream_status.id))

    assert response.status_code == 403
