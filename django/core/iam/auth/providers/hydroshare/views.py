import requests
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2LoginView,
    OAuth2CallbackView,
)


class HydroShareOAuth2Adapter(OAuth2Adapter):
    provider_id = "hydroshare"

    access_token_url = "https://www.hydroshare.org/o/token/"
    authorize_url = "https://www.hydroshare.org/o/authorize/"
    profile_url = "https://www.hydroshare.org/hsapi/userInfo/"

    def complete_login(self, request, app, token, **kwargs):
        headers = {"Authorization": f"Bearer {token.token}"}
        response = requests.get(self.profile_url, headers=headers)
        response.raise_for_status()
        extra_data = response.json()

        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(HydroShareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(HydroShareOAuth2Adapter)
