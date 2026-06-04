from allauth.socialaccount import app_settings
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.orcid.views import OrcidOAuth2Adapter


class SandboxOrcidOAuth2Adapter(OrcidOAuth2Adapter):
    provider_id = "orcidsandbox"

    member_api_default = False
    base_domain_default = "sandbox.orcid.org"

    settings = app_settings.PROVIDERS.get(provider_id, {})

    base_domain = settings.get("BASE_DOMAIN", base_domain_default)
    member_api = settings.get("MEMBER_API", member_api_default)

    api_domain = "{0}.{1}".format("api" if member_api else "pub", base_domain)

    authorize_url = "https://{0}/oauth/authorize".format(base_domain)
    access_token_url = "https://{0}/oauth/token".format(api_domain)
    profile_url = "https://{0}/v3.0/%s/record".format(api_domain)


oauth2_login = OAuth2LoginView.adapter_view(SandboxOrcidOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(SandboxOrcidOAuth2Adapter)
