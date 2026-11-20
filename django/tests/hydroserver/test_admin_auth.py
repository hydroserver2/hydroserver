from urllib.parse import quote

import pytest
from django.urls import reverse

from tests.core.iam.factories import UserFactory

pytestmark = pytest.mark.django_db

ADMIN_PAGE = "/admin/iam/user/"


def test_anonymous_admin_access_redirects_to_account_login(client):
    response = client.get(ADMIN_PAGE)

    assert response.status_code == 302
    login_redirect = response.url
    response = client.get(login_redirect)

    assert response.status_code == 302
    assert response.url == f"{reverse('account_login')}?next={quote(ADMIN_PAGE)}"


def test_admin_login_page_never_renders_django_form(client):
    response = client.get(reverse("admin:login"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_admin_login_rejects_external_next(client):
    response = client.get(f"{reverse('admin:login')}?next=https://evil.example.com/")

    assert response.url == (
        f"{reverse('account_login')}?next={quote(reverse('admin:index'))}"
    )


def test_account_login_returns_to_admin_page(client):
    user = UserFactory(is_staff=True, password="password")

    response = client.post(
        reverse("account_login"),
        {"login": user.email, "password": "password", "next": ADMIN_PAGE},
    )

    assert response.status_code == 302
    assert response.url == ADMIN_PAGE


def test_non_staff_user_is_sent_to_profile_with_banner(client):
    client.force_login(UserFactory())

    response = client.get(ADMIN_PAGE, follow=True)

    assert response.redirect_chain[-1][0] == reverse("account_profile")
    assert b"permission to access the admin dashboard" in response.content


def test_staff_user_can_access_admin(client):
    client.force_login(UserFactory(is_staff=True, is_superuser=True))

    assert client.get(ADMIN_PAGE).status_code == 200


def test_staff_user_on_admin_login_is_sent_to_next(client):
    client.force_login(UserFactory(is_staff=True))

    response = client.get(f"{reverse('admin:login')}?next={ADMIN_PAGE}")

    assert response.url == ADMIN_PAGE


def test_admin_logout_uses_allauth(client):
    client.force_login(UserFactory(is_staff=True))

    response = client.post(reverse("admin:logout"))

    assert response.url == reverse("account_logout")


def test_admin_password_change_uses_allauth(client):
    client.force_login(UserFactory(is_staff=True))

    response = client.get(reverse("admin:password_change"))

    assert response.url == reverse("account_change_password")
