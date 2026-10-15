import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from allauth.socialaccount.providers.openid_connect.provider import OpenIDConnectProvider
from django.contrib.sites.models import Site
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
        "last_name": "Doe",
        "user_type": "Researcher",
    }
    data.update(overrides)
    return data


def test_signup_persists_profile_fields(client):
    client.post(reverse("account_signup"), data=_signup_data())

    user = User.objects.get(email="new-user@example.com")
    assert user.first_name == "Jane"
    assert user.last_name == "Doe"
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
    client.post(
        reverse("account_signup"),
        data=_signup_data(
            has_organization=False,
            org_name="Organization that must not be created",
            org_code="NONE",
            org_description="This information was submitted while unchecked.",
            org_link="https://example.com",
            org_type="University",
        ),
    )

    user = User.objects.get(email="new-user@example.com")
    assert user.organization is None
    assert Organization.objects.count() == 0


def test_signup_hides_and_disables_organization_fields_by_default(client):
    response = client.get(reverse("account_signup"))

    assert response.status_code == 200
    assert b'id="id_has_organization" checked' not in response.content
    assert (
        b'id="org-fields" class="auth-organization-fields" hidden disabled'
        in response.content
    )
    assert b"toggleOrganizationFields" in response.content


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


@pytest.fixture
def utahid_signup(client):
    app = SocialApp.objects.create(
        provider="openid_connect",
        provider_id="utahid",
        name="UtahID",
        client_id="test-client",
        settings={"server_url": "https://identity.example.test"},
    )
    app.sites.add(Site.objects.get_current())
    sociallogin = SocialLogin(
        provider=OpenIDConnectProvider(request=None, app=app),
        account=SocialAccount(provider="utahid", uid="test-utahid-user"),
        user=User(email="utahid-user@example.com", first_name="Jane", last_name="Doe"),
        email_addresses=[
            EmailAddress(email="utahid-user@example.com", verified=True, primary=True)
        ],
    )
    session = client.session
    session["socialaccount_sociallogin"] = sociallogin.serialize()
    session.save()
    return client


def test_social_signup_renders_public_vocabulary_as_dropdowns(utahid_signup):
    UserType.objects.create(name="Internal only", public=False)
    OrganizationType.objects.create(name="Private organization", public=False)

    response = utahid_signup.get(reverse("socialaccount_signup"))

    assert response.status_code == 200
    assert b'<select name="user_type"' in response.content
    assert b'<option value="Researcher">Researcher</option>' in response.content
    assert b'<select name="org_type"' in response.content
    assert b'<option value="University">University</option>' in response.content
    assert b"Internal only" not in response.content
    assert b"Private organization" not in response.content


def test_social_signup_hides_organization_fields_until_affiliated(utahid_signup):
    response = utahid_signup.get(reverse("socialaccount_signup"))

    content = response.content.decode()
    org_fields = content.index('id="org-fields"')
    assert "hidden disabled" in content[org_fields : content.index(">", org_fields)]
    assert content.index('name="org_name"') > org_fields
    assert "toggleOrganizationFields" in content


def test_social_signup_preserves_selected_choices_after_validation_error(utahid_signup):
    response = utahid_signup.post(
        reverse("socialaccount_signup"),
        data={
            "email": "utahid-user@example.com",
            "user_type": "Researcher",
            "has_organization": True,
            "org_type": "University",
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors.get("org_name")
    assert b'<option value="Researcher" selected>Researcher</option>' in response.content
    assert b'<option value="University" selected>University</option>' in response.content
    assert b'id="id_has_organization" checked' in response.content
    assert b'id="org-fields" class="auth-organization-fields" >' in response.content
    assert not User.objects.filter(email="utahid-user@example.com").exists()


def test_social_signup_saves_account_type_and_organization(utahid_signup):
    utahid_signup.post(
        reverse("socialaccount_signup"),
        data={
            "email": "utahid-user@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "user_type": "Researcher",
            "has_organization": True,
            "org_name": "Utah State University",
            "org_code": "USU",
            "org_type": "University",
        },
    )

    user = User.objects.get(email="utahid-user@example.com")
    assert user.user_type == "Researcher"
    assert user.organization.organization_type == "University"
    assert SocialAccount.objects.get(user=user).provider == "utahid"
