"""
Request-level checks that credentials which are sent but fail to validate are
rejected, rather than falling through to anonymous access on public endpoints.
"""

import base64
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from tests.core.iam.factories import ServiceAccountFactory, UserFactory

pytestmark = pytest.mark.django_db

PUBLIC_URL = "/api/ogc/collections/units/items"
PRIVATE_URL = "/api/ogc/collections/data-product-transformations/items"
ST_THINGS_URL = "/api/sensorthings/v1.1/Things"


def _api_key(**overrides):
    service_account = ServiceAccountFactory()
    raw_key = service_account.generate_key()
    for field, value in overrides.items():
        setattr(service_account, field, value)
    service_account.save()
    return raw_key


def _basic(username, password):
    return "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()


BAD_CREDENTIALS = {
    "apikey_unknown": (lambda: {"HTTP_X_API_KEY": "abcdefghijklmnopqrstuvwxyz"}, "Invalid API key"),
    "apikey_short": (lambda: {"HTTP_X_API_KEY": "abc"}, "Invalid API key"),
    "apikey_wrong_secret": (lambda: {"HTTP_X_API_KEY": _api_key()[:12] + "wrong-secret"}, "Invalid API key"),
    "apikey_expired": (
        lambda: {"HTTP_X_API_KEY": _api_key(key_expires_at=timezone.now() - timedelta(days=1))},
        "API key has expired",
    ),
    "apikey_inactive": (lambda: {"HTTP_X_API_KEY": _api_key(is_active=False)}, "Invalid API key"),
    "bearer_unknown": (
        lambda: {"HTTP_AUTHORIZATION": "Bearer not-a-real-token"},
        "Invalid or expired access token",
    ),
    "basic_wrong_password": (
        lambda: {"HTTP_AUTHORIZATION": _basic(UserFactory().email, "wrong")},
        "Invalid username or password",
    ),
    "basic_malformed": (
        lambda: {"HTTP_AUTHORIZATION": "Basic !!!not-base64"},
        "Invalid or unsupported credentials",
    ),
    "unknown_scheme": (
        lambda: {"HTTP_AUTHORIZATION": "Token abc123"},
        "Invalid or unsupported credentials",
    ),
}


@pytest.mark.parametrize("case", list(BAD_CREDENTIALS))
def test_bad_credentials_are_rejected_on_public_endpoint(client, case):
    headers, message = BAD_CREDENTIALS[case]

    response = client.get(PUBLIC_URL, **headers())

    assert response.status_code == 401
    assert response.json() == {"message": message}


@pytest.mark.parametrize("case", list(BAD_CREDENTIALS))
def test_bad_credentials_are_rejected_on_private_endpoint(client, case):
    headers, _ = BAD_CREDENTIALS[case]

    response = client.get(PRIVATE_URL, **headers())

    assert response.status_code == 401


def test_invalid_bearer_token_sets_www_authenticate_header(client):
    response = client.get(PUBLIC_URL, HTTP_AUTHORIZATION="Bearer not-a-real-token")

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == 'Bearer error="invalid_token"'


def test_no_credentials_are_anonymous_on_public_endpoint(client):
    assert client.get(PUBLIC_URL).status_code == 200


def test_no_credentials_are_rejected_on_private_endpoint(client):
    assert client.get(PRIVATE_URL).status_code == 401


def test_stale_session_cookie_is_anonymous_on_public_endpoint(client):
    client.cookies[settings.SESSION_COOKIE_NAME] = "does-not-exist"

    assert client.get(PUBLIC_URL).status_code == 200


def test_valid_api_key_is_accepted(client):
    response = client.get(PUBLIC_URL, HTTP_X_API_KEY=_api_key())

    assert response.status_code == 200


def test_expired_api_key_is_rejected_even_with_valid_basic_credentials(client):
    user = UserFactory()
    user.set_password("correct-password")
    user.save()

    response = client.get(
        PUBLIC_URL,
        HTTP_X_API_KEY=_api_key(key_expires_at=timezone.now() - timedelta(days=1)),
        HTTP_AUTHORIZATION=_basic(user.email, "correct-password"),
    )

    assert response.status_code == 401


def test_valid_session_wins_over_expired_api_key(client):
    client.force_login(UserFactory())

    response = client.get(
        PRIVATE_URL,
        HTTP_X_API_KEY=_api_key(key_expires_at=timezone.now() - timedelta(days=1)),
    )

    assert response.status_code == 200


def test_expired_api_key_is_rejected_on_sensorthings_read(client):
    response = client.get(
        ST_THINGS_URL,
        HTTP_X_API_KEY=_api_key(key_expires_at=timezone.now() - timedelta(days=1)),
    )

    assert response.status_code == 401


def test_expired_api_key_is_rejected_on_sensorthings_write(client):
    response = client.post(
        ST_THINGS_URL,
        data={"name": "Thing", "description": "Thing"},
        content_type="application/json",
        HTTP_X_API_KEY=_api_key(key_expires_at=timezone.now() - timedelta(days=1)),
    )

    assert response.status_code == 401
