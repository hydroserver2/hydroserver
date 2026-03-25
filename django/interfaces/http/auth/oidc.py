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
        with request_context(request):
            claims = decode_jwt_token(
                token,
                client_id=None,
                verify_exp=True,
                verify_iss=True,
            )

        if not claims or claims.get("token_use") != "access":
            return None

        client_id = claims.get("client_id")
        sub = claims.get("sub")
        if not isinstance(client_id, str) or not isinstance(sub, str):
            return None

        client = Client.objects.filter(id=client_id).first()
        if not client:
            return None

        with request_context(request):
            return get_adapter().get_user_by_sub(client, sub)
