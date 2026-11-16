from urllib.parse import urlencode

import pytest

from allauth.account.models import EmailAddress
from allauth.idp.oidc.models import Client
from django.contrib.messages import get_messages
from django.test import RequestFactory, override_settings
from django.urls import reverse

from core.iam.models import User, UserType
from core.iam.templatetags.account_navigation import (
    RETURN_URL_SESSION_KEY,
    account_back_link,
)


pytestmark = pytest.mark.django_db

WEB_CLIENT_URL = "https://app.example.test"
CALLBACK = "https://third-party.example.test/callback"


@pytest.fixture
def oidc_client():
    return Client.objects.create(
        id="third-party",
        name="Third Party App",
        redirect_uris=f"{CALLBACK}\n{CALLBACK}?tenant=1",
    )


def authorize_url(**params):
    return f"{reverse('idp:oidc:authorization')}?{urlencode(params)}"


@pytest.mark.parametrize(
    "next_url, expected_url, expected_label",
    [
        (f"{WEB_CLIENT_URL}/browse", f"{WEB_CLIENT_URL}/browse", "Go back to HydroServer"),
        ("/accounts/profile/", "/accounts/profile/", "Go back to HydroServer"),
        ("http://localhost:1203/workspaces", "http://localhost:1203/workspaces", "Go back"),
        ("https://untrusted.example.test/", WEB_CLIENT_URL, "Go back to HydroServer"),
        (None, WEB_CLIENT_URL, "Go back to HydroServer"),
    ],
)
def test_account_back_link_labels_the_return_destination(
    settings, next_url, expected_url, expected_label
):
    settings.WEB_CLIENT_URL = WEB_CLIENT_URL
    settings.ACCOUNT_RETURN_URL_ALLOWED_HOSTS = {"localhost:1203"}
    request = RequestFactory().get("/accounts/login/", {"next": next_url} if next_url else {})

    assert account_back_link({"request": request}) == {
        "url": expected_url,
        "label": expected_label,
    }


@pytest.mark.parametrize(
    "params, expected_url, expected_label",
    [
        (
            {"client_id": "third-party", "redirect_uri": CALLBACK, "state": "xyz"},
            f"{CALLBACK}?error=access_denied&state=xyz",
            "Go back to Third Party App",
        ),
        (
            {"client_id": "third-party", "redirect_uri": CALLBACK},
            f"{CALLBACK}?error=access_denied",
            "Go back to Third Party App",
        ),
        (
            {"client_id": "third-party", "redirect_uri": f"{CALLBACK}?tenant=1"},
            f"{CALLBACK}?tenant=1&error=access_denied",
            "Go back to Third Party App",
        ),
        (
            {"client_id": "third-party", "redirect_uri": "https://evil.example.test/"},
            WEB_CLIENT_URL,
            "Go back to HydroServer",
        ),
        (
            {"client_id": "unknown", "redirect_uri": CALLBACK},
            WEB_CLIENT_URL,
            "Go back to HydroServer",
        ),
    ],
)
@pytest.mark.parametrize("on_consent_page", [False, True])
def test_account_back_link_cancels_oidc_sign_in(
    settings, oidc_client, params, expected_url, expected_label, on_consent_page
):
    settings.WEB_CLIENT_URL = WEB_CLIENT_URL
    if on_consent_page:
        request = RequestFactory().get(authorize_url(**params))
    else:
        request = RequestFactory().get("/accounts/login/", {"next": authorize_url(**params)})

    assert account_back_link({"request": request}) == {
        "url": expected_url,
        "label": expected_label,
    }


@override_settings(WEB_CLIENT_URL="http://127.0.0.1:1203")
def test_account_flow_preserves_the_go_back_link(client, oidc_client):
    destination = "http://127.0.0.1:1203/browse?tab=sites#recent"

    login_response = client.get(reverse("account_login"), {"next": destination})
    reset_response = client.get(reverse("account_reset_password"))

    assert login_response.status_code == 200
    assert client.session[RETURN_URL_SESSION_KEY] == destination
    assert b'href="http://127.0.0.1:1203/browse?tab=sites#recent"' in reset_response.content
    assert b"Go back to HydroServer" in reset_response.content

    next_url = authorize_url(client_id="third-party", redirect_uri=CALLBACK, state="xyz")
    client.get(reverse("account_login"), {"next": next_url})
    reset_response = client.get(reverse("account_reset_password"))

    assert b"Go back to Third Party App" in reset_response.content
    assert f'href="{CALLBACK}?error=access_denied&amp;state=xyz"'.encode() in reset_response.content


@override_settings(WEB_CLIENT_URL="http://127.0.0.1:1203")
def test_login_returns_to_the_frontend_destination(client):
    user = User.objects.create_user(
        email="return-to-app@example.test",
        password="password",
        user_type="Other",
    )
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    destination = "http://127.0.0.1:1203/browse?tab=sites#recent"

    response = client.post(
        reverse("account_login"),
        {"login": user.email, "password": "password", "next": destination},
    )

    assert response.status_code == 302
    assert response["Location"] == destination
    assert list(get_messages(response.wsgi_request)) == []


def test_invalid_login_keeps_inline_errors(client):
    response = client.post(
        reverse("account_login"),
        {"login": "missing@example.test", "password": "incorrect"},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert b"hs-alert--error" in response.content
    assert list(get_messages(response.wsgi_request)) == []


def test_profile_edit_does_not_queue_a_success_message(client):
    UserType.objects.update_or_create(name="Other", defaults={"public": True})
    user = User.objects.create_user(
        email="edit-without-flash@example.test",
        password="password",
        user_type="Other",
    )
    client.force_login(user)

    response = client.post(
        reverse("account_profile_edit"),
        {"first_name": "Updated", "last_name": "User", "user_type": "Other"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.first_name == "Updated"
    assert list(get_messages(response.wsgi_request)) == []


def test_profile_page_loads_the_account_navigation_tag(client):
    user = User.objects.create_user(
        email="profile@example.test",
        password="password",
        user_type="Other",
    )
    client.force_login(user)

    response = client.get(reverse("account_profile"))

    assert response.status_code == 200
    assert b"/static/design-system/html.css" in response.content
    assert b"/static/design-system/django.css" not in response.content
    assert b"/static/css/auth.css" in response.content
    assert b"tailwind.css" not in response.content


def test_profile_edit_hides_organization_fields_without_an_affiliation(client):
    user = User.objects.create_user(
        email="profile-edit@example.test",
        password="password",
        user_type="Other",
    )
    client.force_login(user)

    response = client.get(reverse("account_profile_edit"))

    assert response.status_code == 200
    assert b'id="id_has_organization" checked' not in response.content
    assert b'id="org-fields" class="auth-organization-fields" hidden' in response.content


def test_login_page_uses_the_shared_design_system_styles(client):
    response = client.get(reverse("account_login"))

    assert response.status_code == 200
    assert b"/static/design-system/html.css" in response.content
    assert b"/static/design-system/django.css" not in response.content
    assert b"/static/css/auth.css" in response.content
    assert b"Sign in to HydroServer" in response.content
    assert b"Remember Me" not in response.content
    assert b"/static/img/favicon-32x32.png" in response.content
    assert b"/static/img/favicon-16x16.png" in response.content
    assert b"tailwind.css" not in response.content
