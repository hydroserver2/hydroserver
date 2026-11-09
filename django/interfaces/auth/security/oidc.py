from allauth.idp.oidc.contrib.ninja.security import TokenAuth
from interfaces.api.http.errors import InvalidTokenError, PermissionDeniedError


class OIDCAuth(TokenAuth):
    """
    Authenticates via an OIDC access token, delegating validation (expiry,
    revocation, and resource/audience checks) to allauth's own
    oauthlib-backed TokenAuth. Sets request.principal for consistency with
    the other auth classes in this package.
    """

    def __init__(self, scope: str) -> None:
        super().__init__(scope=None)
        self.required_scope = scope

    def __call__(self, request):
        scheme, _, _ = request.headers.get("Authorization", "").partition(" ")

        if scheme.lower() != "bearer":
            return None

        access_token = super().__call__(request)
        if not access_token:
            raise InvalidTokenError("Invalid or expired access token")

        if not access_token.user:
            raise PermissionDeniedError("Access token is not associated with a user")

        if self.required_scope not in access_token.get_scopes():
            raise PermissionDeniedError(
                f"Access token is missing the required scope: {self.required_scope}"
            )

        request.principal = access_token.user

        return access_token.user
