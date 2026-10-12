import pytest
from django.urls import reverse

from core.iam.models import Organization, OrganizationType, User


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser(email="admin@example.test", password="password")
    client.force_login(admin)
    return client


def _user_with_organization(organization_type):
    organization = Organization.objects.create(
        name="Utah State University", code="USU", organization_type=organization_type
    )
    return User.objects.create_user(
        email="profile@example.test", password="password", user_type="Other",
        organization=organization,
    )


def _profile_data(**overrides):
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "user_type": "Other",
        "has_organization": True,
        "org_name": "USU",
        "org_code": "USU",
    }
    data.update(overrides)
    return data


def test_profile_edit_without_public_organization_types_offers_other(client):
    user = User.objects.create_user(
        email="profile@example.test", password="password", user_type="Other"
    )
    client.force_login(user)

    page = client.get(reverse("account_profile_edit"))
    client.post(reverse("account_profile_edit"), _profile_data(org_type="Other"))

    assert page.context["form"].fields["org_type"].choices == [("Other", "Other")]
    user.refresh_from_db()
    assert user.organization.organization_type == "Other"


def test_profile_edit_keeps_unlisted_organization_type(client):
    OrganizationType.objects.create(name="University", public=True)
    user = _user_with_organization("Retired Type")
    client.force_login(user)

    page = client.get(reverse("account_profile_edit"))
    response = client.post(reverse("account_profile_edit"), _profile_data(org_type="Retired Type"))

    assert ("Retired Type", "Retired Type") in page.context["form"].fields["org_type"].choices
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.organization.organization_type == "Retired Type"


def test_organization_admin_lists_organizations(admin_client):
    _user_with_organization("University")

    response = admin_client.get(reverse("admin:iam_organization_changelist"))

    assert response.status_code == 200
    assert b"Utah State University" in response.content
    assert b"profile@example.test" in response.content


def test_organization_type_admin_loads_defaults(admin_client):
    changelist = admin_client.get(reverse("admin:iam_organizationtype_changelist"))
    preview = admin_client.get(reverse("admin:iam_organizationtype_load_defaults"))
    response = admin_client.post(reverse("admin:iam_organizationtype_load_defaults"))

    assert reverse("admin:iam_organizationtype_load_defaults").encode() in changelist.content
    assert "University" in {str(obj) for obj, _ in preview.context["to_create"]}
    assert response.status_code == 302
    assert OrganizationType.objects.filter(name="University").exists()
