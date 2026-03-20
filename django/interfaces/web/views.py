from allauth.socialaccount.models import SocialApp
from django.templatetags.static import static
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.conf import settings
from domains.web.models import InstanceConfiguration, MapLayer, ContactInformation


@cache_page(60 * 10)
def index(request):

    instance_configuration = InstanceConfiguration.get_configuration()
    contact_information = ContactInformation.objects.all()
    map_layers = MapLayer.objects.all()
    social_apps = SocialApp.objects.all()

    context = {
        "authenticationConfiguration": {
            "hydroserverSignupEnabled": settings.ACCOUNT_SIGNUP_ENABLED,
            "providers": [
                {
                    "id": social_app.provider_id,
                    "name": social_app.name,
                    "iconLink": f"{settings.PROXY_BASE_URL if settings.DEPLOYMENT_BACKEND == 'local' else ''}"
                    f"{static(f'providers/{social_app.provider_id}.png')}",
                    "signupEnabled": (
                        True
                        if social_app.settings.get("allowSignUp") is not False
                        else False
                    ),
                    "connectEnabled": (
                        True
                        if social_app.settings.get("allowConnection") is True
                        else False
                    ),
                }
                for social_app in social_apps
            ],
        },
        "aboutInformation": {
            "showAboutInformation": instance_configuration.show_about_information,
            "title": instance_configuration.about_page_title,
            "text": instance_configuration.about_page_text,
            "contactOptions": [
                {
                    "title": contact_option.title,
                    "text": contact_option.text,
                    "action": contact_option.action,
                    "icon": contact_option.icon,
                    "link": contact_option.link,
                }
                for contact_option in contact_information
            ],
        },
        "mapConfiguration": {
            "defaultLatitude": instance_configuration.map_configuration.default_latitude,
            "defaultLongitude": instance_configuration.map_configuration.default_longitude,
            "defaultZoomLevel": instance_configuration.map_configuration.default_zoom_level,
            "defaultBaseLayer": getattr(
                instance_configuration.map_configuration.default_base_layer,
                "name",
                None,
            ),
            "defaultSatelliteLayer": getattr(
                instance_configuration.map_configuration.default_satellite_layer,
                "name",
                None,
            ),
            "elevationService": instance_configuration.map_configuration.elevation_service,
            "geoService": instance_configuration.map_configuration.geo_service,
            "basemapLayers": [
                {
                    "name": map_layer.name,
                    "source": map_layer.source,
                    "attribution": map_layer.attribution,
                }
                for map_layer in map_layers
                if map_layer.type == "basemap"
            ],
            "overlayLayers": [
                {
                    "name": map_layer.name,
                    "source": map_layer.source,
                    "attribution": map_layer.attribution,
                    "priority": map_layer.priority,
                }
                for map_layer in map_layers
                if map_layer.type == "overlay"
            ],
        },
        "analyticsConfiguration": {
            "enableClarityAnalytics": instance_configuration.analytics_configuration.enable_clarity_analytics,
            "clarityProjectId": instance_configuration.analytics_configuration.clarity_project_id,
        },
        "legalInformation": {
            "termsOfUseLink": instance_configuration.terms_of_use_link,
            "privacyPolicyLink": instance_configuration.privacy_policy_link,
            "copyright": instance_configuration.copyright,
        },
    }

    return render(request, "index.html", {"settings": context})
