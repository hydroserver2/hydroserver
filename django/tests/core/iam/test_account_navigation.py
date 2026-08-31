import pytest

from allauth.account.models import EmailAddress
from django.test import RequestFactory, override_settings
from django.urls import reverse

from core.iam.models import User
from core.iam.templatetags.account_navigation import (
    RETURN_URL_SESSION_KEY,
    account_back_url,
)


pytestmark = pytest.mark.django_db


@override_settings(WEB_CLIENT_URL="https://app.example.test")
def test_account_back_url_uses_the_calling_app_destination():
    request = RequestFactory().get(
        "/accounts/login/?next=https://app.example.test/browse"
    )

    assert account_back_url({"request": request}) == "https://app.example.test/browse"


@override_settings(WEB_CLIENT_URL="https://app.example.test")
def test_account_back_url_rejects_untrusted_destinations_and_uses_web_client():
    request = RequestFactory().get(
        "/accounts/login/?next=https://untrusted.example.test/"
    )

    assert account_back_url({"request": request}) == "https://app.example.test"


@override_settings(WEB_CLIENT_URL="http://127.0.0.1:1203")
def test_account_back_url_uses_web_client_when_no_destination_is_supplied():
    request = RequestFactory().get("/accounts/password/reset/")

    assert account_back_url({"request": request}) == "http://127.0.0.1:1203"


@override_settings(
    WEB_CLIENT_URL="http://127.0.0.1:1203",
    ACCOUNT_RETURN_URL_ALLOWED_HOSTS={"localhost:1203"},
)
def test_account_back_url_accepts_configured_calling_app_host():
    request = RequestFactory().get(
        "/accounts/profile/?next=http://localhost:1203/workspaces"
    )

    assert account_back_url({"request": request}) == "http://localhost:1203/workspaces"


@override_settings(WEB_CLIENT_URL="http://127.0.0.1:1203")
def test_account_flow_preserves_frontend_destination_for_the_go_back_link(client):
    destination = "http://127.0.0.1:1203/browse?tab=sites#recent"

    login_response = client.get(reverse("account_login"), {"next": destination})
    reset_response = client.get(reverse("account_reset_password"))

    assert login_response.status_code == 200
    assert client.session[RETURN_URL_SESSION_KEY] == destination
    assert b'href="http://127.0.0.1:1203/browse?tab=sites#recent"' in reset_response.content


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
