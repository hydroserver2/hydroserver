import time
import uuid

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from allauth.core.internal import jwkkit
from allauth.idp.oidc.adapter import get_adapter
from allauth.idp.oidc.models import Client as OIDCClient


User = get_user_model()


@pytest.fixture
def oidc_logout_client():
    client = OIDCClient.objects.create(
        id="test-logout-client",
        name="Test Logout Client",
        type=OIDCClient.Type.PUBLIC,
    )
    client.set_scopes(["openid", "profile", "email"])
    client.set_grant_types(
        [OIDCClient.GrantType.AUTHORIZATION_CODE, OIDCClient.GrantType.REFRESH_TOKEN]
    )
    client.set_response_types(["code"])
    client.set_redirect_uris(["https://rp.example/callback"])
    client.save()
    return client


def _build_id_token_hint(user, oidc_client, settings, issuer="http://testserver"):
    now = int(time.time())
    claims = {
        "aud": oidc_client.id,
        "iss": issuer,
        "iat": now,
        "exp": now + 300,
        "jti": uuid.uuid4().hex,
        "sub": get_adapter().get_user_sub(oidc_client, user),
    }
    jwk_dict, private_key = jwkkit.load_jwk_from_pem(settings.IDP_OIDC_PRIVATE_KEY)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": jwk_dict["kid"]},
    )


def test_logout_without_id_token_hint_requires_confirmation(client):
    user = User.objects.get(email="owner@example.com")
    client.force_login(user)

    response = client.get(
        reverse("idp:oidc:logout"),
        {
            "post_logout_redirect_uri": "https://rp.example/logout",
            "state": "opaque-state",
        },
    )

    assert response.status_code == 200
    assert b"Yes, sign out" in response.content
    assert client.session.get("_auth_user_id") == str(user.pk)


def test_logout_with_valid_id_token_hint_completes_immediately(
    client, oidc_logout_client, settings
):
    user = User.objects.get(email="owner@example.com")
    client.force_login(user)
    id_token_hint = _build_id_token_hint(user, oidc_logout_client, settings)

    response = client.get(
        reverse("idp:oidc:logout"),
        {
            "id_token_hint": id_token_hint,
            "post_logout_redirect_uri": "https://rp.example/logout",
            "state": "opaque-state",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "https://rp.example/logout?state=opaque-state"
    assert "_auth_user_id" not in client.session
