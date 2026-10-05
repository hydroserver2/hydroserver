from datetime import timedelta

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import timezone
from ninja.errors import HttpError

from allauth.core.context import request_context
from allauth.idp.oidc.models import Client, Token

from core.iam.auth.oidc_adapter import HydroServerOIDCAdapter
from core.iam.auth.scopes import DATA_READ, DATA_WRITE
from interfaces.auth.security import OIDCAuth, oidc_read_auth, oidc_write_auth
from tests.core.iam.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def oidc_client():
    client = Client.objects.create(
        id="test-oidc-client",
        name="Test OIDC Client",
        type=Client.Type.PUBLIC,
    )
    client.set_scopes(["openid", "profile", "email", DATA_READ, DATA_WRITE])
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
    _access_token(
        oidc_client, user, "valid-token", scopes=["openid", DATA_READ]
    )
    request = _bearer_request("valid-token")

    with request_context(request):
        result = oidc_read_auth(request)

    assert result == user
    assert request.principal == user


def test_oidc_auth_returns_none_without_authorization_header():
    request = _bearer_request(None)

    with request_context(request):
        result = oidc_read_auth(request)

    assert result is None
    assert not hasattr(request, "principal")


def test_oidc_auth_returns_none_for_unknown_token():
    request = _bearer_request("does-not-exist")

    with request_context(request):
        result = oidc_read_auth(request)

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
        result = oidc_read_auth(request)

    assert result is None


def test_oidc_auth_returns_none_for_inactive_users_token(oidc_client):
    user = UserFactory(inactive=True)
    _access_token(oidc_client, user, "inactive-user-token")
    request = _bearer_request("inactive-user-token")

    with request_context(request):
        result = oidc_read_auth(request)

    assert result is None


@pytest.mark.parametrize(
    "auth, scopes",
    [
        (oidc_read_auth, []),
        (oidc_read_auth, ["openid", DATA_WRITE]),
        (oidc_write_auth, []),
        (oidc_write_auth, ["openid", DATA_READ]),
    ],
)
def test_oidc_auth_rejects_token_missing_required_scope(oidc_client, auth, scopes):
    """A valid token without the required scope is rejected outright rather
    than returning None, which would fall through to anonymous_auth."""
    user = UserFactory()
    _access_token(oidc_client, user, "wrong-scope-token", scopes=scopes)
    request = _bearer_request("wrong-scope-token")

    with request_context(request), pytest.raises(HttpError) as exc_info:
        auth(request)

    assert exc_info.value.status_code == 403
    assert not hasattr(request, "principal")


def test_oidc_write_auth_authenticates_write_scoped_token(oidc_client):
    user = UserFactory()
    _access_token(oidc_client, user, "write-token", scopes=["openid", DATA_WRITE])
    request = _bearer_request("write-token")

    with request_context(request):
        result = oidc_write_auth(request)

    assert result == user
    assert request.principal == user


# --- Scope enforcement on the Data Management and SensorThings APIs --------------


def _bearer(value):
    return {"HTTP_AUTHORIZATION": f"Bearer {value}"}


@pytest.mark.parametrize(
    "path",
    ["/api/data/workspaces", "/api/sensorthings/v1.1/Things"],
)
def test_read_endpoint_scope_enforcement(client, oidc_client, path):
    user = UserFactory()
    _access_token(oidc_client, user, "read-token", scopes=["openid", DATA_READ])
    _access_token(oidc_client, user, "write-token", scopes=["openid", DATA_WRITE])
    _access_token(oidc_client, user, "no-scope-token", scopes=["openid"])

    assert client.get(path, **_bearer("read-token")).status_code == 200
    assert client.get(path, **_bearer("write-token")).status_code == 403
    assert client.get(path, **_bearer("no-scope-token")).status_code == 403
    assert client.get(path).status_code == 200  # anonymous access is unaffected


def test_data_api_write_endpoint_scope_enforcement(client, oidc_client):
    user = UserFactory()
    _access_token(oidc_client, user, "read-token", scopes=["openid", DATA_READ])
    _access_token(oidc_client, user, "write-token", scopes=["openid", DATA_WRITE])

    def create_workspace(token):
        return client.post(
            "/api/data/workspaces",
            {"name": f"Workspace {token}", "isPrivate": True},
            content_type="application/json",
            **_bearer(token),
        )

    assert create_workspace("read-token").status_code == 403
    assert create_workspace("write-token").status_code == 201


@pytest.mark.parametrize(
    "path", ["/api/sensorthings/v1.1/Observations", "/api/sensorthings/v1.1/CreateObservations"]
)
def test_sensorthings_write_endpoint_rejects_read_scoped_token(client, oidc_client, path):
    user = UserFactory()
    _access_token(oidc_client, user, "read-token", scopes=["openid", DATA_READ])

    response = client.post(
        path, {}, content_type="application/json", **_bearer("read-token")
    )

    assert response.status_code == 403


def _oidc_auths(operation):
    # The SensorThings router wraps sync auth handlers in sync_to_async.
    callbacks = [getattr(cb, "func", cb) for cb in operation.auth_callbacks]
    return [cb for cb in callbacks if isinstance(cb, OIDCAuth)]


def _api_operations(api):
    for prefix, router in api._routers:
        for path, path_view in router.path_operations.items():
            for operation in path_view.operations:
                yield f"{prefix}/{path}", operation


@pytest.mark.parametrize(
    "api_module",
    ["interfaces.api.urls", "sensorthings.versions.v1_1.urls"],
)
def test_every_endpoint_requires_matching_oidc_scope(api_module):
    """Guards against new endpoints accepting OIDC tokens without a scope, or
    accepting read-scoped tokens for writes."""
    from importlib import import_module

    api = import_module(api_module).api
    checked = 0

    for path, operation in _api_operations(api):
        for auth in _oidc_auths(operation):
            expected = DATA_READ if operation.methods == ["GET"] else DATA_WRITE
            assert auth.required_scope == expected, (
                f"{operation.methods} {path} requires {auth.required_scope!r}, "
                f"expected {expected!r}"
            )
            checked += 1

    assert checked > 0


def test_oidc_authorization_form_uses_clear_consent_language(oidc_client):
    rendered = render_to_string(
        "idp/oidc/authorization_form.html",
        {"client": oidc_client},
        request=RequestFactory().get("/identity/o/authorize"),
    )

    assert "Test OIDC Client would like to access your HydroServer account." in rendered
    assert "Review the permissions below before continuing." in rendered
    assert "Authorize" in rendered
    assert "Cancel" in rendered


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


def test_adapter_describes_data_scopes_on_consent_screen():
    scope_display = HydroServerOIDCAdapter.scope_display

    assert DATA_READ in scope_display
    assert DATA_WRITE in scope_display
    assert "openid" in scope_display


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
