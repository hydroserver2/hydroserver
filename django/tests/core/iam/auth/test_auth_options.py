from html import escape
from urllib.parse import urlencode

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.urls import reverse

from core.iam.models import User


pytestmark = pytest.mark.django_db
DESTINATION = "https://app.example.test/browse?tab=sites#recent"


@pytest.fixture(autouse=True)
def calling_app(settings):
    settings.WEB_CLIENT_URL = "https://app.example.test"


@pytest.fixture(params=["account_login", "account_signup"])
def auth_page(request):
    return request.param


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


def test_auth_offers_email_and_provider_buttons_with_the_return_destination(client, utahid, auth_page):
    response = client.get(reverse(auth_page), {"next": DESTINATION})
    content = response.content.decode()

    email_url = "?" + urlencode({"next": DESTINATION, "method": "email"})
    provider_url = reverse("openid_connect_login", kwargs={"provider_id": "utahid"})
    provider_url += "?" + urlencode({"process": "login", "next": DESTINATION})
    assert response.status_code == 200
    assert f'href="{escape(email_url)}"' in content
    assert f'href="{escape(provider_url)}"' in content
    assert content.index("Continue with UtahID") < content.index("Continue with email")
    assert 'name="login"' not in content
    assert 'name="email"' not in content
    assert 'type="password"' not in content


def test_email_choice_opens_the_form_and_preserves_the_return_destination(client, utahid, auth_page):
    response = client.get(
        reverse(auth_page), {"method": "email", "next": DESTINATION}
    )
    content = response.content.decode()

    assert response.status_code == 200
    email_field = "login" if auth_page == "account_login" else "email"
    assert f'name="{email_field}"' in content
    assert 'type="password"' in content
    assert response.context["redirect_field_value"] == DESTINATION
    other_options = "Other sign-in options" if auth_page == "account_login" else "Other sign-up options"
    assert other_options in content
    assert "Continue with UtahID" not in content
    options_url = reverse(auth_page) + "?" + urlencode({"next": DESTINATION})
    assert f'href="{escape(options_url)}"' in content


def test_invalid_email_login_stays_on_the_form_with_inline_errors(client, utahid):
    response = client.post(
        reverse("account_login"),
        {"login": "missing@example.test", "password": "incorrect", "next": DESTINATION},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert b"hs-alert--error" in response.content
    assert b'name="login"' in response.content
    assert b'type="password"' in response.content
    assert b"Other sign-in options" in response.content
    assert response.context["redirect_field_value"] == DESTINATION


def test_email_login_still_authenticates_and_returns_to_the_app(client, utahid):
    user = User.objects.create_user(
        email="email-choice@example.test", password="password", user_type="Other"
    )
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    client.get(reverse("account_login"), {"method": "email", "next": DESTINATION})

    response = client.post(
        reverse("account_login"),
        {"login": user.email, "password": "password", "next": DESTINATION},
    )

    assert response.status_code == 302
    assert response["Location"] == DESTINATION
    assert client.session["_auth_user_id"] == str(user.pk)


def test_auth_without_providers_opens_the_email_form_directly(client, auth_page):
    response = client.get(reverse(auth_page))

    assert response.status_code == 200
    email_field = "login" if auth_page == "account_login" else "email"
    assert f'name="{email_field}"'.encode() in response.content
    assert b'type="password"' in response.content
    assert b"Continue with email" not in response.content


def test_hidden_providers_do_not_trigger_the_choice_page(client, utahid, auth_page):
    utahid.settings["hidden"] = True
    utahid.save()

    response = client.get(reverse(auth_page))

    email_field = "login" if auth_page == "account_login" else "email"
    assert f'name="{email_field}"'.encode() in response.content
    assert b"Continue with UtahID" not in response.content


def test_social_only_auth_never_offers_the_email_route(client, utahid, settings, auth_page):
    settings.SOCIALACCOUNT_ONLY = True

    response = client.get(reverse(auth_page), {"method": "email"})

    assert response.status_code == 200
    assert b"Continue with UtahID" in response.content
    assert b"Continue with email" not in response.content
    assert b'name="login"' not in response.content
    assert b'name="email"' not in response.content


def test_invalid_email_signup_keeps_the_form_values_and_return_destination(client, utahid):
    response = client.post(
        reverse("account_signup"),
        {
            "email": "new-email-choice@example.test",
            "password1": "a-very-strong-password-123",
            "password2": "does-not-match",
            "user_type": "Other",
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
    assert b"Other sign-up options" in response.content
    assert response.context["redirect_field_value"] == DESTINATION
    assert not User.objects.filter(email="new-email-choice@example.test").exists()


def test_email_signup_with_a_provider_still_creates_an_account(client, utahid):
    client.get(reverse("account_signup"), {"method": "email", "next": DESTINATION})
    response = client.post(
        reverse("account_signup"),
        {
            "email": "new-email-choice@example.test",
            "password1": "a-very-strong-password-123",
            "password2": "a-very-strong-password-123",
            "user_type": "Other",
            "next": DESTINATION,
        },
    )

    assert response.status_code == 302
    user = User.objects.get(email="new-email-choice@example.test")
    assert EmailAddress.objects.filter(user=user, verified=False).exists()
