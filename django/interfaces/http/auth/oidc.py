from django.conf import settings
from allauth.core.context import request_context
from allauth.idp.oidc.adapter import get_adapter
from allauth.idp.oidc.internal.tokens import decode_jwt_token
from allauth.idp.oidc.models import Client, Token
from ninja.errors import HttpError
from ninja.security import HttpBearer


class OIDCAuth(HttpBearer):
    def authenticate(self, request, token):
        user = self._authenticate_opaque_token(token)
        if user is None:
            user = self._authenticate_jwt_token(request, token)

        if user and user.is_authenticated and user.is_active:
            request.user = user
            request.principal = user
            return user
        elif token:
            raise HttpError(401, "Invalid token")

    def _authenticate_opaque_token(self, token):
        access_token = Token.objects.lookup(Token.Type.ACCESS_TOKEN, token)
        if not access_token or not access_token.user:
            return None
        if not access_token.user.is_active:
            return None
        return access_token.user

    def _authenticate_jwt_token(self, request, token):
        claims = None
        validated_client_id = None

        with request_context(request):
            for client_id in self._get_allowed_client_ids():
                claims = decode_jwt_token(
                    token,
                    client_id=client_id,
                    verify_exp=True,
                    verify_iss=True,
                )
                if claims:
                    validated_client_id = client_id
                    break

        if not claims or claims.get("token_use") != "access":
            return None

        client_id = claims.get("client_id")
        sub = claims.get("sub")
        if (
            not isinstance(client_id, str)
            or client_id != validated_client_id
            or not isinstance(sub, str)
        ):
            return None

        client = Client.objects.filter(id=client_id).first()
        if not client:
            return None

        with request_context(request):
            return get_adapter().get_user_by_sub(client, sub)

    def _get_allowed_client_ids(self):
        client_ids = []
        for client_config in getattr(settings, "OIDC_BUNDLED_CLIENTS", {}).values():
            client_id = client_config.get("id")
            if isinstance(client_id, str) and client_id not in client_ids:
                client_ids.append(client_id)
        return client_ids
