import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import ObservedPropertyTypeFactory

pytestmark = pytest.mark.django_db

OBSERVED_PROPERTY_TYPES_URL = "/api/data/observed-property-types"


def _detail_url(observed_property_type_id):
    return f"{OBSERVED_PROPERTY_TYPES_URL}/{observed_property_type_id}"


def _observed_property_type_body(**overrides):
    body = {
        "name": "New Type",
        "description": "A new observed property type.",
    }
    body.update(overrides)
    return body


# --- get_observed_property_types --------------------------------------------------------------


def test_get_observed_property_types_visible_to_anonymous(client):
    observed_property_type = ObservedPropertyTypeFactory()

    response = client.get(OBSERVED_PROPERTY_TYPES_URL)

    assert response.status_code == 200
    assert str(observed_property_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_observed_property_types_visible_to_any_authenticated_user(client):
    observed_property_type = ObservedPropertyTypeFactory()
    client.force_login(UserFactory())

    response = client.get(OBSERVED_PROPERTY_TYPES_URL)

    assert response.status_code == 200
    assert str(observed_property_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_observed_property_types_properties_filters_every_item_in_the_list(client):
    ObservedPropertyTypeFactory(name="A")
    ObservedPropertyTypeFactory(name="B")

    response = client.get(OBSERVED_PROPERTY_TYPES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_observed_property_types_properties_rejects_unknown_property(client):
    response = client.get(OBSERVED_PROPERTY_TYPES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_observed_property_types_without_properties_returns_every_field(client):
    ObservedPropertyTypeFactory(name="A")

    response = client.get(OBSERVED_PROPERTY_TYPES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_observed_property_types_q_searches_name_and_description(client):
    ObservedPropertyTypeFactory(name="Alpha term", description="")
    ObservedPropertyTypeFactory(name="Beta term", description="")

    response = client.get(OBSERVED_PROPERTY_TYPES_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_observed_property_types_sortby_name_descending(client):
    ObservedPropertyTypeFactory(name="Alpha")
    ObservedPropertyTypeFactory(name="Beta")

    response = client.get(OBSERVED_PROPERTY_TYPES_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_observed_property_type ------------------------------------------------------------


def test_create_observed_property_type_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        OBSERVED_PROPERTY_TYPES_URL,
        data=_observed_property_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    observed_property_type_id = response.json()["id"]

    detail = client.get(_detail_url(observed_property_type_id))
    assert detail.json()["data"]["name"] == "New Type"


def test_create_observed_property_type_returns_401_when_unauthenticated(client):
    response = client.post(
        OBSERVED_PROPERTY_TYPES_URL,
        data=_observed_property_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_observed_property_type_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        OBSERVED_PROPERTY_TYPES_URL,
        data=_observed_property_type_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_observed_property_type_returns_400_for_duplicate_name(client):
    ObservedPropertyTypeFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        OBSERVED_PROPERTY_TYPES_URL,
        data=_observed_property_type_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_observed_property_type ----------------------------------------------------------------


def test_get_observed_property_type_returns_200_for_anonymous(client):
    observed_property_type = ObservedPropertyTypeFactory()

    response = client.get(_detail_url(observed_property_type.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(observed_property_type.id)


def test_get_observed_property_type_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_observed_property_type_properties_rejects_unknown_property(client):
    observed_property_type = ObservedPropertyTypeFactory()

    response = client.get(_detail_url(observed_property_type.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_observed_property_type -------------------------------------------------------------


def test_update_observed_property_type_succeeds_for_superuser(client):
    observed_property_type = ObservedPropertyTypeFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(observed_property_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(observed_property_type.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_observed_property_type_returns_401_when_unauthenticated(client):
    observed_property_type = ObservedPropertyTypeFactory()

    response = client.patch(
        _detail_url(observed_property_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_observed_property_type_returns_403_for_non_superuser(client):
    observed_property_type = ObservedPropertyTypeFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(observed_property_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_observed_property_type -------------------------------------------------------------


def test_delete_observed_property_type_succeeds_for_superuser(client):
    observed_property_type = ObservedPropertyTypeFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(observed_property_type.id))

    assert response.status_code == 204
    assert client.get(_detail_url(observed_property_type.id)).status_code == 404


def test_delete_observed_property_type_returns_403_for_non_superuser(client):
    observed_property_type = ObservedPropertyTypeFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(observed_property_type.id))

    assert response.status_code == 403
