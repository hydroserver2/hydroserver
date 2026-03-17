from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from domains.iam.auth.providers.hydroshare.views import HydroShareOAuth2Adapter


class HydroShareAccount(ProviderAccount):
    def to_str(self):
        return self.account.extra_data.get("name", super().to_str())


class HydroShareProvider(OAuth2Provider):
    id = "hydroshare"
    name = "HydroShare"
    account_class = HydroShareAccount
    oauth2_adapter_class = HydroShareOAuth2Adapter

    def get_default_scope(self):
        return ["read", "write"]

    def extract_uid(self, data):
        return str(data["id"])

    def extract_common_fields(self, data):
        return dict(
            email=data.get("email"),
            last_name=data.get("last_name"),
            first_name=data.get("first_name"),
        )


provider_classes = [HydroShareProvider]
