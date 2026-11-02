from datetime import timedelta

import pytest
from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.utils import timezone

from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import PermissionDeniedError, UnauthorizedError
from interfaces.auth.security import anonymous_auth, apikey_auth, session_auth
from tests.core.iam.factories import ServiceAccountFactory, UserFactory

pytestmark = pytest.mark.django_db


def _service_account_with_key(**overrides):
    service_account = ServiceAccountFactory()
    raw_key = service_account.generate_key()
    for field, value in overrides.items():
        setattr(service_account, field, value)
    service_account.save()
    return service_account, raw_key


# --- APIKeyAuth (interfaces/auth/security/apikey.py) -------------------------------


def test_apikey_auth_returns_none_without_header():
    request = RequestFactory().get("/")

    assert apikey_auth(request) is None


def test_apikey_auth_authenticates_valid_key():
    service_account, raw_key = _service_account_with_key()
    request = RequestFactory().get("/", HTTP_X_API_KEY=raw_key)

    assert apikey_auth(request) == service_account
    assert request.principal == service_account
    service_account.refresh_from_db()
    assert service_account.last_used_at is not None


def test_apikey_auth_accepts_key_expiring_in_future():
    service_account, raw_key = _service_account_with_key(
        key_expires_at=timezone.now() + timedelta(days=1)
    )
    request = RequestFactory().get("/", HTTP_X_API_KEY=raw_key)

    assert apikey_auth(request) == service_account


@pytest.mark.parametrize(
    "make_key, message",
    [
        (lambda: "abc", "Invalid API key"),
        (lambda: "abcdefghijklmnopqrstuvwxyz", "Invalid API key"),
        (lambda: _service_account_with_key()[1][:12] + "wrong-secret", "Invalid API key"),
        (lambda: _service_account_with_key(is_active=False)[1], "Invalid API key"),
        (
            lambda: _service_account_with_key(key_expires_at=timezone.now() - timedelta(days=1))[1],
            "API key has expired",
        ),
    ],
    ids=["short", "unknown", "wrong_secret", "inactive", "expired"],
)
def test_apikey_auth_raises_for_invalid_key(make_key, message):
    request = RequestFactory().get("/", HTTP_X_API_KEY=make_key())

    with pytest.raises(UnauthorizedError) as exc_info:
        apikey_auth(request)

    assert str(exc_info.value) == message
    assert not hasattr(request, "principal")


def test_apikey_auth_rejects_deactivated_account():
    service_account, raw_key = _service_account_with_key()
    service_account.deactivate()
    request = RequestFactory().get("/", HTTP_X_API_KEY=raw_key)

    with pytest.raises(UnauthorizedError):
        apikey_auth(request)


# --- anonymous_auth (interfaces/auth/security/anonymous.py) ------------------------


def test_anonymous_auth_sets_anonymous_principal_without_credentials():
    request = RequestFactory().get("/")

    assert anonymous_auth(request) is True
    assert isinstance(request.principal, AnonymousPrincipal)


@pytest.mark.parametrize(
    "header",
    ["HTTP_AUTHORIZATION", "HTTP_X_API_KEY"],
)
def test_anonymous_auth_rejects_requests_with_credential_headers(header):
    request = RequestFactory().get("/", **{header: "anything"})

    with pytest.raises(UnauthorizedError):
        anonymous_auth(request)

    assert not hasattr(request, "principal")


def test_anonymous_auth_matches_api_key_header_case_insensitively():
    request = RequestFactory().get("/", headers={"X-API-KEY": "anything"})

    with pytest.raises(UnauthorizedError):
        anonymous_auth(request)


def test_anonymous_auth_ignores_session_cookie():
    request = RequestFactory().get("/")
    request.COOKIES[django_settings.SESSION_COOKIE_NAME] = "stale"

    assert anonymous_auth(request) is True


# --- SessionAuth (interfaces/auth/security/session.py) -----------------------------


def _session_request(method="post", user=None, **extra):
    request = getattr(RequestFactory(), method)("/", **extra)
    request.COOKIES[django_settings.SESSION_COOKIE_NAME] = "session-key"
    request.user = user if user is not None else UserFactory()
    return request


@pytest.fixture
def strict_security(settings):
    settings.STRICT_SECURITY = True


def test_session_auth_returns_none_without_cookie():
    request = RequestFactory().get("/")
    request.user = UserFactory()

    assert session_auth(request) is None


def test_session_auth_returns_none_for_stale_session(strict_security):
    request = _session_request(user=AnonymousUser())

    assert session_auth(request) is None


def test_session_auth_authenticates_safe_method_without_csrf_token(strict_security):
    request = _session_request(method="get")

    assert session_auth(request) == request.user
    assert request.principal == request.user


def test_session_auth_rejects_failed_csrf_check(strict_security):
    request = _session_request()

    with pytest.raises(PermissionDeniedError) as exc_info:
        session_auth(request)

    assert str(exc_info.value) == "CSRF check failed"
    assert not hasattr(request, "principal")


def test_session_auth_defers_failed_csrf_check_to_credential_header(strict_security):
    request = _session_request(HTTP_X_API_KEY="some-api-key")

    assert session_auth(request) is None


def test_session_auth_skips_csrf_for_exempt_operations(strict_security):
    request = _session_request()
    request._ninja_csrf_exempt = True

    assert session_auth(request) == request.user


def test_session_auth_skips_csrf_without_strict_security(settings):
    settings.STRICT_SECURITY = False
    request = _session_request()

    assert session_auth(request) == request.user
