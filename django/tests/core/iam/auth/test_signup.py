import pytest
from django.urls import reverse

from core.iam.models import Organization, OrganizationType, User, UserType

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def vocabulary():
    UserType.objects.create(name="Researcher", public=True)
    OrganizationType.objects.create(name="University", public=True)


def _signup_data(**overrides):
    data = {
        "email": "new-user@example.com",
        "password1": "a-very-strong-password-123",
        "password2": "a-very-strong-password-123",
        "first_name": "Jane",
        "middle_name": "Q",
        "last_name": "Doe",
        "phone": "555-0100",
        "address": "123 Main St",
        "link": "https://example.com",
        "user_type": "Researcher",
    }
    data.update(overrides)
    return data


def test_signup_persists_profile_fields(client):
    client.post(reverse("account_signup"), data=_signup_data())

    user = User.objects.get(email="new-user@example.com")
    assert user.first_name == "Jane"
    assert user.middle_name == "Q"
    assert user.last_name == "Doe"
    assert user.phone == "555-0100"
    assert user.address == "123 Main St"
    assert user.link == "https://example.com"
    assert user.user_type == "Researcher"
    assert user.organization is None


def test_signup_creates_and_links_organization(client):
    client.post(
        reverse("account_signup"),
        data=_signup_data(
            has_organization=True,
            org_name="Utah State University",
            org_code="USU",
            org_description="A public university",
            org_link="https://usu.edu",
            org_type="University",
        ),
    )

    user = User.objects.get(email="new-user@example.com")
    assert user.organization is not None
    assert user.organization.name == "Utah State University"
    assert user.organization.code == "USU"
    assert user.organization.description == "A public university"
    assert user.organization.link == "https://usu.edu"
    assert user.organization.organization_type == "University"
    assert Organization.objects.count() == 1


def test_signup_without_organization_leaves_it_unset(client):
    client.post(reverse("account_signup"), data=_signup_data(has_organization=False))

    user = User.objects.get(email="new-user@example.com")
    assert user.organization is None
    assert Organization.objects.count() == 0


def test_signup_requires_organization_fields_when_affiliated(client):
    response = client.post(
        reverse("account_signup"),
        data=_signup_data(has_organization=True),
    )

    assert not User.objects.filter(email="new-user@example.com").exists()
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors.get("org_name")
    assert form.errors.get("org_code")
    assert form.errors.get("org_type")