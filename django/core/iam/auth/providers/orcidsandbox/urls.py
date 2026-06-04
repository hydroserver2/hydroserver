from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import SandboxOrcidProvider


urlpatterns = default_urlpatterns(SandboxOrcidProvider)
