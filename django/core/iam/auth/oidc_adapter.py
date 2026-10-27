from allauth.idp.oidc.adapter import DefaultOIDCAdapter

from core.iam.auth.scopes import SCOPES


class HydroServerOIDCAdapter(DefaultOIDCAdapter):
    """
    Adds HydroServer-specific profile claims (organization, account type,
    etc.) to the /userinfo response, using the same shape as the SPA
    shell's embedded current-user context (interfaces/web/views.py).

    Kept out of the ID token to keep it lean and only returned to clients
    that request the standard "profile" scope.

    HydroServer has no usernames, so allauth omits the standard
    "preferred_username" claim. The user's email stands in for it in both
    the ID token and /userinfo, but only for clients that were also granted
    the "email" scope.
    """

    scope_display = {
        **DefaultOIDCAdapter.scope_display,
        **{scope: definition.label for scope, definition in SCOPES.items()},
    }

    def get_claims(self, purpose, user, client, scopes, email=None, **kwargs):
        claims = super().get_claims(
            purpose, user, client, scopes, email=email, **kwargs
        )

        if "profile" in scopes and "email" in scopes and user.email:
            claims.setdefault("preferred_username", user.email)

        if purpose == "userinfo" and "profile" in scopes:
            claims.update(user.to_profile_claims())

        return claims
