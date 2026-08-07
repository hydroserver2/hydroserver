from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from allauth.core.context import request_context
from allauth.idp.oidc.models import Client, Token

from core.iam.auth.oidc_adapter import HydroServerOIDCAdapter
from interfaces.auth.security import oidc_auth
from tests.core.iam.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def oidc_client():
    client = Client.objects.create(
        id="test-oidc-client",
        name="Test OIDC Client",
        type=Client.Type.PUBLIC,
    )
    client.set_scopes(["openid", "profile", "email"])
    client.set_grant_types(
        [Client.GrantType.AUTHORIZATION_CODE, Client.GrantType.REFRESH_TOKEN]
    )
    client.set_response_types(["code"])
    client.save()
    return client


def _access_token(oidc_client, user, value, scopes=None, expires_at=None):
    token = Token(
        client=oidc_client,
        user=user,
        type=Token.Type.ACCESS_TOKEN,
        expires_at=expires_at,
    )
    token.set_value(value)
    token.set_scopes(scopes if scopes is not None else ["openid", "profile", "email"])
    token.save()
    return token


def _bearer_request(token_value=None):
    request = RequestFactory().get("/api/data/workspaces")
    if token_value is not None:
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token_value}"
    return request


# --- OIDCAuth (interfaces/auth/security/oidc.py) -----------------------------------


def test_oidc_auth_authenticates_valid_access_token(oidc_client):
    user = UserFactory()
    _access_token(oidc_client, user, "valid-token")
    request = _bearer_request("valid-token")

    with request_context(request):
        result = oidc_auth(request)

    assert result == user
    assert request.principal == user


def test_oidc_auth_returns_none_without_authorization_header():
    request = _bearer_request(None)

    with request_context(request):
        result = oidc_auth(request)

    assert result is None
    assert not hasattr(request, "principal")


def test_oidc_auth_returns_none_for_unknown_token():
    request = _bearer_request("does-not-exist")

    with request_context(request):
        result = oidc_auth(request)

    assert result is None


def test_oidc_auth_returns_none_for_expired_token(oidc_client):
    user = UserFactory()
    _access_token(
        oidc_client,
        user,
        "expired-token",
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    request = _bearer_request("expired-token")

    with request_context(request):
        result = oidc_auth(request)

    assert result is None


def test_oidc_auth_returns_none_for_inactive_users_token(oidc_client):
    user = UserFactory(inactive=True)
    _access_token(oidc_client, user, "inactive-user-token")
    request = _bearer_request("inactive-user-token")

    with request_context(request):
        result = oidc_auth(request)

    assert result is None


def test_oidc_auth_succeeds_regardless_of_granted_scopes(oidc_client):
    """oidc_auth is configured with scope=None (no scope taxonomy exists yet),
    so a token with no scopes at all is still accepted."""
    user = UserFactory()
    _access_token(oidc_client, user, "no-scopes-token", scopes=[])
    request = _bearer_request("no-scopes-token")

    with request_context(request):
        result = oidc_auth(request)

    assert result == user


# --- HydroServerOIDCAdapter (core/iam/auth/oidc_adapter.py) ------------------------


def test_userinfo_includes_custom_claims_when_profile_scope_granted(oidc_client):
    adapter = HydroServerOIDCAdapter()
    user = UserFactory(superuser=True)

    claims = adapter.get_claims(
        "userinfo", user, oidc_client, ["openid", "profile", "email"]
    )

    expected = user.to_profile_claims()
    for key, value in expected.items():
        assert claims[key] == value
    assert claims["accountType"] == "admin"


def test_userinfo_omits_custom_claims_without_profile_scope(oidc_client):
    adapter = HydroServerOIDCAdapter()
    user = UserFactory()

    claims = adapter.get_claims("userinfo", user, oidc_client, ["openid"])

    assert "accountType" not in claims
    assert "organization" not in claims


def test_id_token_never_gets_custom_claims(oidc_client):
    adapter = HydroServerOIDCAdapter()
    user = UserFactory()

    claims = adapter.get_claims(
        "id_token", user, oidc_client, ["openid", "profile", "email"]
    )

    assert "accountType" not in claims
    assert "organization" not in claims


# --- /identity/o/api/userinfo end-to-end --------------------------------------------


def test_userinfo_endpoint_returns_custom_claims(client, oidc_client):
    user = UserFactory(first_name="Jane", last_name="Doe")
    _access_token(oidc_client, user, "e2e-token")

    response = client.get(
        "/identity/o/api/userinfo", HTTP_AUTHORIZATION="Bearer e2e-token"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["firstName"] == "Jane"
    assert body["accountType"] == "standard"


def test_userinfo_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/identity/o/api/userinfo", HTTP_AUTHORIZATION="Bearer invalid-token"
    )

    assert response.status_code == 401
