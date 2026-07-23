import pytest

from core.iam.models import Organization, OrganizationType, UserType
from tests.core.iam.factories import UserFactory

pytestmark = pytest.mark.django_db

ACCOUNT_URL = "/api/auth/browser/account"


# --- get_account ---------------------------------------------------------------------


def test_get_account_returns_200_for_authenticated_user(client):
    user = UserFactory(first_name="Jane", last_name="Doe")
    client.force_login(user)

    response = client.get(ACCOUNT_URL)

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_get_account_returns_401_when_unauthenticated(client):
    response = client.get(ACCOUNT_URL)

    assert response.status_code == 401


# --- update_account ------------------------------------------------------------------


def test_update_account_succeeds_for_authenticated_user(client):
    user = UserFactory(first_name="Original")
    client.force_login(user)

    response = client.patch(
        ACCOUNT_URL,
        data={"firstName": "Updated"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["firstName"] == "Updated"


def test_update_account_returns_401_when_unauthenticated(client):
    response = client.patch(
        ACCOUNT_URL,
        data={"firstName": "Updated"},
        content_type="application/json",
    )

    assert response.status_code == 401


# --- delete_account ------------------------------------------------------------------


def test_delete_account_succeeds_for_authenticated_user(client):
    user = UserFactory()
    client.force_login(user)

    response = client.delete(ACCOUNT_URL)

    assert response.status_code == 204
    assert client.get(ACCOUNT_URL).status_code == 401


def test_delete_account_returns_401_when_unauthenticated(client):
    response = client.delete(ACCOUNT_URL)

    assert response.status_code == 401


# --- vocabulary endpoints --------------------------------------------------------------


def test_get_user_types_returns_public_type_names(client):
    UserType.objects.create(name="Researcher", public=True)
    UserType.objects.create(name="Hidden", public=False)

    response = client.get(f"{ACCOUNT_URL}/user-types")

    assert response.status_code == 200
    assert response.json() == ["Researcher"]


def test_get_organization_types_returns_public_type_names(client):
    OrganizationType.objects.create(name="University", public=True)
    OrganizationType.objects.create(name="Hidden", public=False)

    response = client.get(f"{ACCOUNT_URL}/organization-types")

    assert response.status_code == 200
    assert response.json() == ["University"]
