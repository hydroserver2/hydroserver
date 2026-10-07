from allauth.idp.oidc.adapter import DefaultOIDCAdapter

from core.iam.auth.scopes import SCOPES


class HydroServerOIDCAdapter(DefaultOIDCAdapter):
    """
    Adds HydroServer-specific profile claims (organization, account type,
    etc.) to the /userinfo response, using the same shape as the SPA
    shell's embedded current-user context (interfaces/web/views.py).

    Kept out of the ID token to keep it lean and only returned to clients
    that request the standard "profile" scope.
    """

    scope_display = {
        **DefaultOIDCAdapter.scope_display,
        **{scope: definition.label for scope, definition in SCOPES.items()},
    }

    def get_claims(self, purpose, user, client, scopes, email=None, **kwargs):
        claims = super().get_claims(
            purpose, user, client, scopes, email=email, **kwargs
        )

        if purpose == "userinfo" and "profile" in scopes:
            claims.update(user.to_profile_claims())

        return claims
