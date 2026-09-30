import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import MethodTypeFactory

pytestmark = pytest.mark.django_db

METHOD_TYPES_URL = "/api/data/method-types"


def _detail_url(method_type_id):
    return f"{METHOD_TYPES_URL}/{method_type_id}"


def _method_type_body(**overrides):
    body = {
        "name": "New Type",
        "description": "A new method type.",
    }
    body.update(overrides)
    return body


# --- get_method_types --------------------------------------------------------------


def test_get_method_types_visible_to_anonymous(client):
    method_type = MethodTypeFactory()

    response = client.get(METHOD_TYPES_URL)

    assert response.status_code == 200
    assert str(method_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_method_types_visible_to_any_authenticated_user(client):
    method_type = MethodTypeFactory()
    client.force_login(UserFactory())

    response = client.get(METHOD_TYPES_URL)

    assert response.status_code == 200
    assert str(method_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_method_types_properties_filters_every_item_in_the_list(client):
    MethodTypeFactory(name="A")
    MethodTypeFactory(name="B")

    response = client.get(METHOD_TYPES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_method_types_properties_rejects_unknown_property(client):
    response = client.get(METHOD_TYPES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_method_types_without_properties_returns_every_field(client):
    MethodTypeFactory(name="A")

    response = client.get(METHOD_TYPES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_method_types_q_searches_name_and_description(client):
    MethodTypeFactory(name="Alpha term", description="")
    MethodTypeFactory(name="Beta term", description="")

    response = client.get(METHOD_TYPES_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_method_types_sortby_name_descending(client):
    MethodTypeFactory(name="Alpha")
    MethodTypeFactory(name="Beta")

    response = client.get(METHOD_TYPES_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_method_type ------------------------------------------------------------


def test_create_method_type_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        METHOD_TYPES_URL,
        data=_method_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    method_type_id = response.json()["id"]

    detail = client.get(_detail_url(method_type_id))
    assert detail.json()["data"]["name"] == "New Type"


def test_create_method_type_returns_401_when_unauthenticated(client):
    response = client.post(
        METHOD_TYPES_URL,
        data=_method_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_method_type_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        METHOD_TYPES_URL,
        data=_method_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_method_type_returns_400_for_duplicate_name(client):
    MethodTypeFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        METHOD_TYPES_URL,
        data=_method_type_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_method_type ----------------------------------------------------------------


def test_get_method_type_returns_200_for_anonymous(client):
    method_type = MethodTypeFactory()

    response = client.get(_detail_url(method_type.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(method_type.id)


def test_get_method_type_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_method_type_properties_rejects_unknown_property(client):
    method_type = MethodTypeFactory()

    response = client.get(_detail_url(method_type.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_method_type -------------------------------------------------------------


def test_update_method_type_succeeds_for_superuser(client):
    method_type = MethodTypeFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(method_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(method_type.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_method_type_returns_401_when_unauthenticated(client):
    method_type = MethodTypeFactory()

    response = client.patch(
        _detail_url(method_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_method_type_returns_403_for_non_superuser(client):
    method_type = MethodTypeFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(method_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_method_type -------------------------------------------------------------


def test_delete_method_type_succeeds_for_superuser(client):
    method_type = MethodTypeFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(method_type.id))

    assert response.status_code == 204
    assert client.get(_detail_url(method_type.id)).status_code == 404


def test_delete_method_type_returns_403_for_non_superuser(client):
    method_type = MethodTypeFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(method_type.id))

    assert response.status_code == 403
