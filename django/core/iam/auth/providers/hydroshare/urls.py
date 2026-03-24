from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import HydroShareProvider


urlpatterns = default_urlpatterns(HydroShareProvider)
