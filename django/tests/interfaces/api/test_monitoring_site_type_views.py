import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import MonitoringSiteTypeFactory

pytestmark = pytest.mark.django_db

MONITORING_SITE_TYPES_URL = "/api/data/monitoring-site-types"


def _detail_url(monitoring_site_type_id):
    return f"{MONITORING_SITE_TYPES_URL}/{monitoring_site_type_id}"


def _monitoring_site_type_body(**overrides):
    body = {
        "name": "New Type",
        "description": "A new monitoring site type.",
    }
    body.update(overrides)
    return body


# --- get_monitoring_site_types --------------------------------------------------------------


def test_get_monitoring_site_types_visible_to_anonymous(client):
    monitoring_site_type = MonitoringSiteTypeFactory()

    response = client.get(MONITORING_SITE_TYPES_URL)

    assert response.status_code == 200
    assert str(monitoring_site_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_monitoring_site_types_visible_to_any_authenticated_user(client):
    monitoring_site_type = MonitoringSiteTypeFactory()
    client.force_login(UserFactory())

    response = client.get(MONITORING_SITE_TYPES_URL)

    assert response.status_code == 200
    assert str(monitoring_site_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_monitoring_site_types_properties_filters_every_item_in_the_list(client):
    MonitoringSiteTypeFactory(name="A")
    MonitoringSiteTypeFactory(name="B")

    response = client.get(MONITORING_SITE_TYPES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_monitoring_site_types_properties_rejects_unknown_property(client):
    response = client.get(MONITORING_SITE_TYPES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_monitoring_site_types_without_properties_returns_every_field(client):
    MonitoringSiteTypeFactory(name="A")

    response = client.get(MONITORING_SITE_TYPES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_monitoring_site_types_q_searches_name_and_description(client):
    MonitoringSiteTypeFactory(name="Alpha term", description="")
    MonitoringSiteTypeFactory(name="Beta term", description="")

    response = client.get(MONITORING_SITE_TYPES_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_monitoring_site_types_sortby_name_descending(client):
    MonitoringSiteTypeFactory(name="Alpha")
    MonitoringSiteTypeFactory(name="Beta")

    response = client.get(MONITORING_SITE_TYPES_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_monitoring_site_type ------------------------------------------------------------


def test_create_monitoring_site_type_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        MONITORING_SITE_TYPES_URL,
        data=_monitoring_site_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    monitoring_site_type_id = response.json()["id"]

    detail = client.get(_detail_url(monitoring_site_type_id))
    assert detail.json()["data"]["name"] == "New Type"


def test_create_monitoring_site_type_returns_401_when_unauthenticated(client):
    response = client.post(
        MONITORING_SITE_TYPES_URL,
        data=_monitoring_site_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_site_type_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        MONITORING_SITE_TYPES_URL,
        data=_monitoring_site_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_monitoring_site_type_returns_400_for_duplicate_name(client):
    MonitoringSiteTypeFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        MONITORING_SITE_TYPES_URL,
        data=_monitoring_site_type_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_monitoring_site_type ----------------------------------------------------------------


def test_get_monitoring_site_type_returns_200_for_anonymous(client):
    monitoring_site_type = MonitoringSiteTypeFactory()

    response = client.get(_detail_url(monitoring_site_type.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(monitoring_site_type.id)


def test_get_monitoring_site_type_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_monitoring_site_type_properties_rejects_unknown_property(client):
    monitoring_site_type = MonitoringSiteTypeFactory()

    response = client.get(_detail_url(monitoring_site_type.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_monitoring_site_type -------------------------------------------------------------


def test_update_monitoring_site_type_succeeds_for_superuser(client):
    monitoring_site_type = MonitoringSiteTypeFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(monitoring_site_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(monitoring_site_type.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_monitoring_site_type_returns_401_when_unauthenticated(client):
    monitoring_site_type = MonitoringSiteTypeFactory()

    response = client.patch(
        _detail_url(monitoring_site_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_monitoring_site_type_returns_403_for_non_superuser(client):
    monitoring_site_type = MonitoringSiteTypeFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(monitoring_site_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_monitoring_site_type -------------------------------------------------------------


def test_delete_monitoring_site_type_succeeds_for_superuser(client):
    monitoring_site_type = MonitoringSiteTypeFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(monitoring_site_type.id))

    assert response.status_code == 204
    assert client.get(_detail_url(monitoring_site_type.id)).status_code == 404


def test_delete_monitoring_site_type_returns_403_for_non_superuser(client):
    monitoring_site_type = MonitoringSiteTypeFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(monitoring_site_type.id))

    assert response.status_code == 403
