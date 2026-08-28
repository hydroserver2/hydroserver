from urllib.parse import urlparse

from django import template
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


register = template.Library()
RETURN_URL_SESSION_KEY = "account_return_url"


def _allowed_hosts(request):
    return {
        request.get_host(),
        urlparse(settings.WEB_CLIENT_URL).netloc,
        *getattr(settings, "ACCOUNT_RETURN_URL_ALLOWED_HOSTS", ()),
    }


def _is_safe_destination(request, destination):
    return bool(destination) and url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts=_allowed_hosts(request),
        require_https=request.is_secure(),
    )


@register.simple_tag(takes_context=True)
def account_back_url(context):
    """Return the frontend destination across the account flow."""
    request = context["request"]
    destination = request.GET.get("next")
    session = getattr(request, "session", None)

    if _is_safe_destination(request, destination):
        if session is not None:
            session[RETURN_URL_SESSION_KEY] = destination
        return destination

    if destination and session is not None:
        session.pop(RETURN_URL_SESSION_KEY, None)

    stored_destination = session.get(RETURN_URL_SESSION_KEY) if session is not None else None
    if _is_safe_destination(request, stored_destination):
        return stored_destination

    if stored_destination and session is not None:
        session.pop(RETURN_URL_SESSION_KEY, None)

    return settings.WEB_CLIENT_URL
