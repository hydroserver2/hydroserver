from allauth.idp.oidc.contrib.ninja.security import TokenAuth


class OIDCAuth(TokenAuth):
    """
    Authenticates via an OIDC access token, delegating validation (expiry,
    revocation, scope, and resource/audience checks) to allauth's own
    oauthlib-backed TokenAuth. Sets request.principal for consistency with
    the other auth classes in this package.
    """

    def __call__(self, request):
        access_token = super().__call__(request)
        if not access_token or not access_token.user:
            return None
        request.principal = access_token.user
        return access_token.user
