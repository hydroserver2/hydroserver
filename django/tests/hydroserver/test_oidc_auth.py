from datetime import timedelta

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import timezone
from ninja.errors import HttpError

from allauth.core.context import request_context
from allauth.idp.oidc.models import Client, Token

from allauth.idp.oidc.forms import AuthorizationForm

from core.iam.auth.oidc_adapter import HydroServerOIDCAdapter
from core.iam.auth.scopes import (
    SCOPES,
    DATA_READ,
    DATA_WRITE,
    WORKSPACE_READ,
    WORKSPACE_WRITE,
    IAM_READ,
    IAM_WRITE,
    TASK_READ,
    TASK_WRITE,
    TASK_RUN,
)
from interfaces.auth.security import (
    OIDCAuth,
    oidc_data_read_auth,
    oidc_data_write_auth,
    oidc_iam_write_auth,
    oidc_task_run_auth,
    oidc_workspace_read_auth,
)
from tests.core.iam.factories import UserFactory, WorkspaceFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def oidc_client():
    client = Client.objects.create(
        id="test-oidc-client",
        name="Test OIDC Client",
        type=Client.Type.PUBLIC,
    )
    client.set_scopes(["openid", "profile", "email", *SCOPES])
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
        result = oidc_data_read_auth(request)

    assert result == user
    assert request.principal == user


def test_oidc_auth_returns_none_without_authorization_header():
    request = _bearer_request(None)

    with request_context(request):
        result = oidc_data_read_auth(request)

    assert result is None
    assert not hasattr(request, "principal")


def test_oidc_auth_returns_none_for_unknown_token():
    request = _bearer_request("does-not-exist")

    with request_context(request):
        result = oidc_data_read_auth(request)

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
        result = oidc_data_read_auth(request)

    assert result is None


def test_oidc_auth_returns_none_for_inactive_users_token(oidc_client):
    user = UserFactory(inactive=True)
    _access_token(oidc_client, user, "inactive-user-token")
    request = _bearer_request("inactive-user-token")

    with request_context(request):
        result = oidc_data_read_auth(request)

    assert result is None


@pytest.mark.parametrize(
    "auth, scopes",
    [
        (oidc_data_read_auth, []),
        (oidc_data_read_auth, ["openid", DATA_WRITE]),
        (oidc_data_write_auth, []),
        (oidc_data_write_auth, ["openid", DATA_READ]),
        (oidc_workspace_read_auth, ["openid", DATA_READ]),
        (oidc_iam_write_auth, ["openid", DATA_WRITE, WORKSPACE_WRITE]),
        (oidc_task_run_auth, ["openid", TASK_READ, TASK_WRITE]),
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
        result = oidc_data_write_auth(request)

    assert result == user
    assert request.principal == user


# --- Scope enforcement on the Data Management and SensorThings APIs --------------


def _bearer(value):
    return {"HTTP_AUTHORIZATION": f"Bearer {value}"}


@pytest.mark.parametrize(
    "path, scope, other_scope",
    [
        ("/api/data/workspaces", WORKSPACE_READ, DATA_READ),
        ("/api/data/monitoring-sites", DATA_READ, WORKSPACE_READ),
        ("/api/sensorthings/v1.1/Things", DATA_READ, WORKSPACE_READ),
    ],
)
def test_read_endpoint_scope_enforcement(client, oidc_client, path, scope, other_scope):
    user = UserFactory()
    _access_token(oidc_client, user, "read-token", scopes=["openid", scope])
    _access_token(oidc_client, user, "other-token", scopes=["openid", other_scope])
    _access_token(oidc_client, user, "no-scope-token", scopes=["openid"])

    assert client.get(path, **_bearer("read-token")).status_code == 200
    assert client.get(path, **_bearer("other-token")).status_code == 403
    assert client.get(path, **_bearer("no-scope-token")).status_code == 403
    assert client.get(path).status_code == 200  # anonymous access is unaffected


def test_workspace_create_requires_workspace_write_scope(client, oidc_client):
    user = UserFactory()
    _access_token(oidc_client, user, "data-token", scopes=["openid", DATA_WRITE])
    _access_token(oidc_client, user, "read-token", scopes=["openid", WORKSPACE_READ])
    _access_token(oidc_client, user, "write-token", scopes=["openid", WORKSPACE_WRITE])

    def create_workspace(token):
        return client.post(
            "/api/data/workspaces",
            {"name": f"Workspace {token}", "isPrivate": True},
            content_type="application/json",
            **_bearer(token),
        )

    assert create_workspace("data-token").status_code == 403
    assert create_workspace("read-token").status_code == 403
    assert create_workspace("write-token").status_code == 201


def test_workspace_delete_requires_workspace_write_scope(client, oidc_client):
    user = UserFactory()
    workspace = WorkspaceFactory(owner=user)
    _access_token(oidc_client, user, "iam-token", scopes=["openid", IAM_WRITE])
    _access_token(oidc_client, user, "write-token", scopes=["openid", WORKSPACE_WRITE])
    url = f"/api/data/workspaces/{workspace.id}"

    assert client.delete(url, **_bearer("iam-token")).status_code == 403
    assert client.delete(url, **_bearer("write-token")).status_code == 204


@pytest.mark.parametrize(
    "method, path",
    [
        ("post", "/api/data/workspaces/{workspace_id}/service-accounts"),
        ("put", "/api/data/workspaces/{workspace_id}/service-accounts/{other_id}/regenerate"),
        ("post", "/api/data/workspaces/{workspace_id}/collaborators"),
        ("post", "/api/data/workspaces/{workspace_id}/transfer"),
        ("post", "/api/data/etl-tasks/{other_id}/trigger"),
        ("post", "/api/data/monitoring-tasks/{other_id}/trigger"),
        ("post", "/api/data/data-product-tasks/{other_id}/trigger"),
    ],
)
def test_data_and_workspace_scopes_cannot_reach_iam_or_task_run_endpoints(
    client, oidc_client, method, path
):
    """A token approved for data and workspace edits must not be able to mint
    API keys, change access, transfer ownership, or run tasks."""
    user = UserFactory()
    workspace = WorkspaceFactory(owner=user)
    _access_token(
        oidc_client,
        user,
        "broad-token",
        scopes=["openid", DATA_READ, DATA_WRITE, WORKSPACE_READ, WORKSPACE_WRITE, TASK_WRITE],
    )
    url = path.format(workspace_id=workspace.id, other_id=workspace.id)

    response = getattr(client, method)(
        url, {}, content_type="application/json", **_bearer("broad-token")
    )

    assert response.status_code == 403
    assert "missing the required scope" in response.json()["detail"]


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


# Every Data Management API collection, keyed by router prefix, with the scope
# its GET routes and its write routes require. ROUTE_SCOPE_OVERRIDES lists the
# routes that differ from their collection's default. A router missing from
# this table fails the test, so new collections must pick their scopes here.
COLLECTION_SCOPES = {
    "workspaces": (WORKSPACE_READ, WORKSPACE_WRITE),
    "workspaces/{workspace_id}/collaborators": (IAM_READ, IAM_WRITE),
    "workspaces/{workspace_id}/service-accounts": (IAM_READ, IAM_WRITE),
    "roles": (IAM_READ, IAM_WRITE),
    "monitoring-sites": (DATA_READ, DATA_WRITE),
    "monitoring-site-types": (DATA_READ, DATA_WRITE),
    "linked-resource-types": (DATA_READ, DATA_WRITE),
    "datastreams": (DATA_READ, DATA_WRITE),
    "datastream-statuses": (DATA_READ, DATA_WRITE),
    "aggregation-statistics": (DATA_READ, DATA_WRITE),
    "observations": (DATA_READ, DATA_WRITE),
    "observed-properties": (DATA_READ, DATA_WRITE),
    "observed-property-types": (DATA_READ, DATA_WRITE),
    "units": (DATA_READ, DATA_WRITE),
    "unit-types": (DATA_READ, DATA_WRITE),
    "methods": (DATA_READ, DATA_WRITE),
    "method-types": (DATA_READ, DATA_WRITE),
    "processing-levels": (DATA_READ, DATA_WRITE),
    "result-qualifiers": (DATA_READ, DATA_WRITE),
    "sampled-mediums": (DATA_READ, DATA_WRITE),
    "quality-control/histories": (DATA_READ, DATA_WRITE),
    "quality-control/histories/{history_id}/sessions": (DATA_READ, DATA_WRITE),
    "quality-control/histories/{history_id}/sessions/{session_id}/operations": (
        DATA_READ,
        DATA_WRITE,
    ),
    "etl-data-connections": (TASK_READ, TASK_WRITE),
    "etl-tasks": (TASK_READ, TASK_WRITE),
    "etl-mappings": (TASK_READ, TASK_WRITE),
    "monitoring-tasks": (TASK_READ, TASK_WRITE),
    "monitoring-rules": (TASK_READ, TASK_WRITE),
    "data-product-tasks": (TASK_READ, TASK_WRITE),
    "data-product-transformations": (TASK_READ, TASK_WRITE),
    "data-product-rating-curves": (TASK_READ, TASK_WRITE),
}

ROUTE_SCOPE_OVERRIDES = {
    ("POST", "workspaces/{workspace_id}/transfer"): IAM_WRITE,
    ("PUT", "workspaces/{workspace_id}/transfer"): IAM_WRITE,
    ("DELETE", "workspaces/{workspace_id}/transfer"): IAM_WRITE,
    ("GET", "monitoring-sites/task-summaries"): TASK_READ,
    ("POST", "etl-tasks/{task_id}/trigger"): TASK_RUN,
    ("POST", "monitoring-tasks/{task_id}/trigger"): TASK_RUN,
    ("POST", "data-product-tasks/{task_id}/trigger"): TASK_RUN,
}


def _route_path(prefix, path):
    return "/".join(part for part in f"{prefix}/{path}".split("/") if part)


def test_every_data_api_endpoint_requires_its_listed_oidc_scope():
    """Guards against new endpoints accepting OIDC tokens without a deliberate
    scope choice, or accepting a scope other than the one listed above."""
    from interfaces.api.urls import api

    checked = 0
    used_overrides = set()

    for prefix, router in api._routers:
        for path, path_view in router.path_operations.items():
            for operation in path_view.operations:
                auths = _oidc_auths(operation)
                if not auths:
                    continue

                route = _route_path(prefix, path)
                assert prefix in COLLECTION_SCOPES, (
                    f"{route} accepts OIDC tokens but its collection {prefix!r} has no "
                    f"entry in COLLECTION_SCOPES"
                )
                read_scope, write_scope = COLLECTION_SCOPES[prefix]

                for method in operation.methods:
                    key = (method, route)
                    if key in ROUTE_SCOPE_OVERRIDES:
                        expected = ROUTE_SCOPE_OVERRIDES[key]
                        used_overrides.add(key)
                    else:
                        expected = read_scope if method == "GET" else write_scope

                    for auth in auths:
                        assert auth.required_scope == expected, (
                            f"{method} {route} requires {auth.required_scope!r}, "
                            f"expected {expected!r}"
                        )
                        checked += 1

    assert checked > 0
    assert used_overrides == set(ROUTE_SCOPE_OVERRIDES), (
        f"Stale ROUTE_SCOPE_OVERRIDES entries: {set(ROUTE_SCOPE_OVERRIDES) - used_overrides}"
    )


def test_every_sensorthings_endpoint_requires_data_scope():
    from sensorthings.versions.v1_1.urls import api

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


def _render_consent(oidc_client, requested_scopes):
    form = AuthorizationForm(
        user=UserFactory(),
        requested_scopes=requested_scopes,
        initial={"request": "{}"},
    )
    return render_to_string(
        "idp/oidc/authorization_form.html",
        {"client": oidc_client, "form": form},
        request=RequestFactory().get("/identity/o/authorize"),
    )


def test_consent_screen_warns_about_iam_write_scope(oidc_client):
    rendered = _render_consent(oidc_client, ["openid", IAM_WRITE])

    assert str(SCOPES[IAM_WRITE].label) in rendered
    assert "hs-alert--danger" in rendered
    assert "keep working after you revoke this app" in rendered


def test_consent_screen_notes_that_tasks_can_write_data(oidc_client):
    rendered = _render_consent(oidc_client, ["openid", TASK_WRITE])

    assert "hs-alert--warning" in rendered
    assert "Tasks can write observations to your datastreams" in rendered
    assert "hs-alert--danger" not in rendered


def test_consent_screen_shows_no_warning_for_read_scopes(oidc_client):
    rendered = _render_consent(
        oidc_client, ["openid", DATA_READ, WORKSPACE_READ, IAM_READ, TASK_READ]
    )

    assert "hs-scope__warning" not in rendered
    for scope in (DATA_READ, WORKSPACE_READ, IAM_READ, TASK_READ):
        assert str(SCOPES[scope].label) in rendered


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


def test_adapter_describes_every_hydroserver_scope_on_consent_screen():
    scope_display = HydroServerOIDCAdapter.scope_display

    for scope, definition in SCOPES.items():
        assert scope_display[scope] == definition.label
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
