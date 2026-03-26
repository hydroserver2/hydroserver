from allauth.idp.oidc.adapter import DefaultOIDCAdapter


class HydroServerOIDCAdapter(DefaultOIDCAdapter):
    def populate_access_token(
        self, access_token: dict, *, client, scopes, user, **kwargs
    ) -> None:
        access_token["aud"] = client.id
