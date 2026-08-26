from urllib.parse import urlparse

from django import template
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


register = template.Library()


@register.simple_tag(takes_context=True)
def account_back_url(context):
    """Return the safe app destination supplied by the TypeScript client."""
    request = context["request"]
    destination = request.GET.get("next")
    app_host = urlparse(settings.WEB_CLIENT_URL).netloc
    allowed_hosts = {
        request.get_host(),
        app_host,
        *getattr(settings, "ACCOUNT_RETURN_URL_ALLOWED_HOSTS", ()),
    }

    if destination and url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return destination

    return "/"
