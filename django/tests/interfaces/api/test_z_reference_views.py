import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import ZReferenceFactory

pytestmark = pytest.mark.django_db

Z_REFERENCES_URL = "/api/ogc/collections/z-references/items"


def _detail_url(z_reference_id):
    return f"{Z_REFERENCES_URL}/{z_reference_id}"


def _z_reference_body(**overrides):
    body = {
        "name": "Depth below ice surface",
        "description": "Vertical distance below the ice surface. Positive z is down.",
    }
    body.update(overrides)
    return body


def test_get_z_references_q_searches_name(client):
    ZReferenceFactory(name="Height above bottom", description="")
    ZReferenceFactory(name="Depth below surface", description="")

    response = client.get(Z_REFERENCES_URL, {"q": "bottom"})

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["data"]] == ["Height above bottom"]


def test_create_z_reference_succeeds_for_superuser(client):
    client.force_login(UserFactory(is_superuser=True))

    response = client.post(Z_REFERENCES_URL, data=_z_reference_body(), content_type="application/json")

    assert response.status_code == 201
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["name"] == "Depth below ice surface"


def test_create_z_reference_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(Z_REFERENCES_URL, data=_z_reference_body(), content_type="application/json")

    assert response.status_code == 403


def test_update_z_reference_succeeds_for_superuser(client):
    z_reference = ZReferenceFactory(name="Original Name")
    client.force_login(UserFactory(is_superuser=True))

    response = client.patch(
        _detail_url(z_reference.id), data={"name": "Updated Name"}, content_type="application/json"
    )

    assert response.status_code == 204
    assert client.get(_detail_url(z_reference.id)).json()["data"]["name"] == "Updated Name"


def test_delete_z_reference_succeeds_for_superuser(client):
    z_reference = ZReferenceFactory()
    client.force_login(UserFactory(is_superuser=True))

    response = client.delete(_detail_url(z_reference.id))

    assert response.status_code == 204
    assert client.get(_detail_url(z_reference.id)).status_code == 404
