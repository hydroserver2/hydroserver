import pytest

from django.test import RequestFactory, override_settings
from django.urls import reverse

from core.iam.models import User
from core.iam.templatetags.account_navigation import account_back_url


pytestmark = pytest.mark.django_db


@override_settings(WEB_CLIENT_URL="https://app.example.test")
def test_account_back_url_uses_the_calling_app_destination():
    request = RequestFactory().get(
        "/accounts/login/?next=https://app.example.test/browse"
    )

    assert account_back_url({"request": request}) == "https://app.example.test/browse"


@override_settings(WEB_CLIENT_URL="https://app.example.test")
def test_account_back_url_rejects_untrusted_destinations():
    request = RequestFactory().get(
        "/accounts/login/?next=https://untrusted.example.test/"
    )

    assert account_back_url({"request": request}) == "/"


@override_settings(
    WEB_CLIENT_URL="http://127.0.0.1:1203",
    ACCOUNT_RETURN_URL_ALLOWED_HOSTS={"localhost:1203"},
)
def test_account_back_url_accepts_configured_calling_app_host():
    request = RequestFactory().get(
        "/accounts/profile/?next=http://localhost:1203/workspaces"
    )

    assert account_back_url({"request": request}) == "http://localhost:1203/workspaces"


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


def test_login_page_uses_the_shared_design_system_styles(client):
    response = client.get(reverse("account_login"))

    assert response.status_code == 200
    assert b"/static/design-system/html.css" in response.content
    assert b"/static/design-system/django.css" not in response.content
    assert b"/static/css/auth.css" in response.content
    assert b"Log in to HydroServer" in response.content
    assert b"/static/img/favicon-32x32.png" in response.content
    assert b"/static/img/favicon-16x16.png" in response.content
    assert b"tailwind.css" not in response.content
