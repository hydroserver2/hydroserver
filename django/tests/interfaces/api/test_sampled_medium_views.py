import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import SampledMediumFactory

pytestmark = pytest.mark.django_db

SAMPLED_MEDIUMS_URL = "/api/data/sampled-mediums"


def _detail_url(sampled_medium_id):
    return f"{SAMPLED_MEDIUMS_URL}/{sampled_medium_id}"


def _sampled_medium_body(**overrides):
    body = {
        "name": "New Medium",
        "description": "A new sampled medium.",
    }
    body.update(overrides)
    return body


# --- get_sampled_mediums --------------------------------------------------------------


def test_get_sampled_mediums_visible_to_anonymous(client):
    sampled_medium = SampledMediumFactory()

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    assert str(sampled_medium.id) in [r["id"] for r in response.json()["data"]]


def test_get_sampled_mediums_visible_to_any_authenticated_user(client):
    sampled_medium = SampledMediumFactory()
    client.force_login(UserFactory())

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    assert str(sampled_medium.id) in [r["id"] for r in response.json()["data"]]


def test_get_sampled_mediums_properties_filters_every_item_in_the_list(client):
    SampledMediumFactory(name="A")
    SampledMediumFactory(name="B")

    response = client.get(SAMPLED_MEDIUMS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_sampled_mediums_properties_rejects_unknown_property(client):
    response = client.get(SAMPLED_MEDIUMS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_sampled_mediums_without_properties_returns_every_field(client):
    SampledMediumFactory(name="A")

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_sampled_mediums_q_searches_name_and_description(client):
    SampledMediumFactory(name="Alpha term", description="")
    SampledMediumFactory(name="Beta term", description="")

    response = client.get(SAMPLED_MEDIUMS_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_sampled_mediums_sortby_name_descending(client):
    SampledMediumFactory(name="Alpha")
    SampledMediumFactory(name="Beta")

    response = client.get(SAMPLED_MEDIUMS_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_sampled_medium ------------------------------------------------------------


def test_create_sampled_medium_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    sampled_medium_id = response.json()["id"]

    detail = client.get(_detail_url(sampled_medium_id))
    assert detail.json()["data"]["name"] == "New Medium"


def test_create_sampled_medium_returns_401_when_unauthenticated(client):
    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_sampled_medium_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_sampled_medium_returns_400_for_duplicate_name(client):
    SampledMediumFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_sampled_medium ----------------------------------------------------------------


def test_get_sampled_medium_returns_200_for_anonymous(client):
    sampled_medium = SampledMediumFactory()

    response = client.get(_detail_url(sampled_medium.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(sampled_medium.id)


def test_get_sampled_medium_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_sampled_medium_properties_rejects_unknown_property(client):
    sampled_medium = SampledMediumFactory()

    response = client.get(_detail_url(sampled_medium.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_sampled_medium -------------------------------------------------------------


def test_update_sampled_medium_succeeds_for_superuser(client):
    sampled_medium = SampledMediumFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(sampled_medium.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_sampled_medium_returns_401_when_unauthenticated(client):
    sampled_medium = SampledMediumFactory()

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_sampled_medium_returns_403_for_non_superuser(client):
    sampled_medium = SampledMediumFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_sampled_medium -------------------------------------------------------------


def test_delete_sampled_medium_succeeds_for_superuser(client):
    sampled_medium = SampledMediumFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(sampled_medium.id))

    assert response.status_code == 204
    assert client.get(_detail_url(sampled_medium.id)).status_code == 404


def test_delete_sampled_medium_returns_403_for_non_superuser(client):
    sampled_medium = SampledMediumFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(sampled_medium.id))

    assert response.status_code == 403
