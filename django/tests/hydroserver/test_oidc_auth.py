import time
import uuid

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from ninja.errors import HttpError

from allauth.core.context import request_context
from allauth.core.internal import jwkkit
from allauth.idp.oidc.adapter import get_adapter
from allauth.idp.oidc.models import Client, Token
from interfaces.http.auth import oidc_auth


User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


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


def test_oidc_auth_authenticates_opaque_access_tokens(request_factory, oidc_client):
    request = request_factory.get("/api/data/workspaces")
    user = User.objects.get(email="owner@example.com")
    token_value = "opaque-access-token-value"

    access_token = Token.objects.create(
        client=oidc_client,
        user=user,
        type=Token.Type.ACCESS_TOKEN,
        hash=get_adapter().hash_token(token_value),
    )
    access_token.set_scopes(["openid", "profile", "email"])
    access_token.save(update_fields=["scopes"])

    authenticated_user = oidc_auth.authenticate(request, token_value)

    assert authenticated_user == user
    assert request.user == user
    assert request.principal == user


def test_oidc_auth_authenticates_jwt_access_tokens(request_factory, oidc_client, settings):
    request = request_factory.get("/api/data/workspaces")
    user = User.objects.get(email="owner@example.com")
    now = int(time.time())
    claims = {
        "client_id": oidc_client.id,
        "iss": request.build_absolute_uri("/").rstrip("/"),
        "iat": now,
        "exp": now + 300,
        "jti": uuid.uuid4().hex,
        "token_use": "access",
        "sub": get_adapter().get_user_sub(oidc_client, user),
    }
    jwk_dict, private_key = jwkkit.load_jwk_from_pem(settings.IDP_OIDC_PRIVATE_KEY)
    token_value = jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": jwk_dict["kid"]},
    )

    with request_context(request):
        authenticated_user = oidc_auth.authenticate(request, token_value)

    assert authenticated_user == user
    assert request.user == user
    assert request.principal == user


def test_oidc_auth_rejects_invalid_access_tokens(request_factory):
    request = request_factory.get("/api/data/workspaces")

    with pytest.raises(HttpError) as exc_info:
        oidc_auth.authenticate(request, "invalid-access-token")

    assert exc_info.value.status_code == 401
