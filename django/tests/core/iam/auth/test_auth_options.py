import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from core.iam.models import User
from core.iam.templatetags.provider_icons import provider_icon


pytestmark = pytest.mark.django_db
DESTINATION = "https://app.example.test/browse?tab=sites#recent"
SIGNUP_DATA = {
    "email": "new-user@example.test",
    "password1": "a-very-strong-password-123",
    "password2": "a-very-strong-password-123",
    "user_type": "Other",
}


@pytest.fixture(autouse=True)
def calling_app(settings):
    settings.WEB_CLIENT_URL = "https://app.example.test"


@pytest.fixture
def utahid():
    app = SocialApp.objects.create(
        provider="openid_connect",
        provider_id="utahid",
        name="UtahID",
        client_id="test-client",
        settings={"server_url": "https://identity.example.test"},
    )
    app.sites.add(Site.objects.get_current())
    return app


@pytest.fixture
def signup_only(settings):
    settings.SOCIALACCOUNT_SIGNUP_ONLY = True


def make_user(email, password=None, **extra):
    user = User.objects.create_user(email=email, password=password, user_type="Other", **extra)
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
    return user


def test_login_shows_the_email_form_then_providers(client, utahid):
    content = client.get(reverse("account_login")).content.decode()

    assert 'type="password"' in content
    assert 'class="hs-divider">or<' in content
    assert content.index('type="password"') < content.index("Continue with UtahID")


@pytest.mark.parametrize("query, form_shown", [({}, False), ({"method": "email"}, True)])
def test_signup_offers_email_as_a_choice_when_providers_exist(client, utahid, query, form_shown):
    content = client.get(reverse("account_signup"), query).content.decode()

    assert ('type="password"' in content) is form_shown
    if form_shown:
        assert "Other sign-up options" in content
    else:
        assert content.index("Continue with email") < content.index('class="hs-divider">or<') < content.index("Continue with UtahID")


def test_invalid_email_login_stays_on_the_form_with_inline_errors(client, utahid):
    response = client.post(
        reverse("account_login"),
        {"login": "missing@example.test", "password": "incorrect", "next": DESTINATION},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert b"hs-alert--error" in response.content
    assert b'type="password"' in response.content
    assert response.context["redirect_field_value"] == DESTINATION


def test_email_login_authenticates_and_returns_to_the_app(client, utahid):
    user = make_user("email-login@example.test", password="password")

    response = client.post(
        reverse("account_login"),
        {"login": user.email, "password": "password", "next": DESTINATION},
    )

    assert response.status_code == 302
    assert response["Location"] == DESTINATION
    assert client.session["_auth_user_id"] == str(user.pk)


def test_invalid_email_signup_keeps_the_form_values_and_return_destination(client, utahid):
    response = client.post(
        reverse("account_signup"),
        {
            **SIGNUP_DATA,
            "password2": "does-not-match",
            "first_name": "Jane",
            "has_organization": True,
            "org_description": "An organization description",
            "next": DESTINATION,
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors.get("password2")
    assert response.context["form"].errors.get("org_name")
    assert response.context["form"]["first_name"].value() == "Jane"
    assert b"An organization description" in response.content
    assert b'id="id_has_organization" checked' in response.content
    assert response.context["redirect_field_value"] == DESTINATION
    assert not User.objects.filter(email=SIGNUP_DATA["email"]).exists()


def test_email_signup_creates_an_unverified_account(client, utahid):
    response = client.post(reverse("account_signup"), SIGNUP_DATA)

    assert response.status_code == 302
    user = User.objects.get(email=SIGNUP_DATA["email"])
    assert EmailAddress.objects.filter(user=user, verified=False).exists()


@pytest.mark.parametrize(
    "query, with_provider, form_shown",
    [
        ({}, True, False),
        ({"next": "/admin/"}, True, True),
        ({"method": "email"}, True, True),
        ({}, False, True),
    ],
)
def test_signup_only_login_shows_the_email_form_only_when_needed(client, signup_only, request, query, with_provider, form_shown):
    if with_provider:
        request.getfixturevalue("utahid")

    response = client.get(reverse("account_login"), query)

    assert (b'type="password"' in response.content) is form_shown


@pytest.mark.parametrize("signup_only_enabled", [False, True])
def test_admin_sign_in_shows_the_email_form_and_providers(client, settings, utahid, signup_only_enabled):
    settings.SOCIALACCOUNT_SIGNUP_ONLY = signup_only_enabled

    content = client.get(reverse("account_login"), {"next": "/admin/"}).content.decode()

    assert 'type="password"' in content
    assert content.index('type="password"') < content.index("Continue with UtahID")


def test_signup_only_hides_and_rejects_email_signup(client, signup_only, utahid):
    page = client.get(reverse("account_signup"))
    response = client.post(reverse("account_signup"), SIGNUP_DATA)

    assert b'type="password"' not in page.content
    assert b"Continue with email" not in page.content
    assert b"Continue with UtahID" in page.content
    assert response.status_code == 200
    assert not User.objects.filter(email=SIGNUP_DATA["email"]).exists()


@pytest.mark.parametrize("is_staff, subject", [(False, "Password Reset Request"), (True, "Password Reset Code")])
def test_signup_only_password_reset_points_provider_users_to_their_provider(client, signup_only, is_staff, subject):
    user = make_user("provider-user@example.test", is_staff=is_staff)

    client.post(reverse("account_reset_password"), {"email": user.email})

    assert len(mail.outbox) == 1
    assert subject in mail.outbox[0].subject


def test_signup_only_blocks_setting_a_password_for_provider_users(client, signup_only):
    user = make_user("provider-user@example.test")
    client.force_login(user)

    client.post(
        reverse("account_set_password"),
        {"password1": "a-very-strong-password-123", "password2": "a-very-strong-password-123"},
    )

    user.refresh_from_db()
    assert not user.has_usable_password()


@pytest.mark.parametrize(
    "provider_id, icon, expected",
    [
        ("github", None, "/static/provider-icons/github.png"),
        ("sso", "provider-icons/google.png", "/static/provider-icons/google.png"),
        ("utahid", None, None),
    ],
)
def test_provider_icon_resolves_existing_files_only(provider_id, icon, expected):
    cache.clear()
    app = SocialApp(provider="openid_connect", provider_id=provider_id, settings={"icon": icon} if icon else {})

    assert provider_icon(app) == expected


def test_sign_in_buttons_show_icons_only_when_the_file_exists(client, utahid):
    cache.clear()
    microsoft = SocialApp.objects.create(
        provider="openid_connect",
        provider_id="microsoft",
        name="Microsoft",
        client_id="client",
        settings={"server_url": "https://login.example.test"},
    )
    microsoft.sites.add(Site.objects.get_current())

    response = client.get(reverse("account_login"))
    content = response.content.decode()

    assert content.count('class="auth-provider-icon"') == 1
    assert '<img src="/static/provider-icons/microsoft.png"' in content
    assert "Continue with UtahID" in content
