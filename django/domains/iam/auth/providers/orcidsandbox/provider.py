from allauth.socialaccount.providers.orcid.provider import (
    Scope,
    OrcidAccount,
    OrcidProvider,
    extract_from_dict,
)
from domains.iam.auth.providers.orcidsandbox.views import SandboxOrcidOAuth2Adapter


class SandboxOrcidProvider(OrcidProvider):
    id = "orcidsandbox"
    name = "sandbox.Orcid.org"
    oauth2_adapter_class = SandboxOrcidOAuth2Adapter


provider_classes = [SandboxOrcidProvider]
