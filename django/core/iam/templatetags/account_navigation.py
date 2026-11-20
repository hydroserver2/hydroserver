from urllib.parse import urlparse

from allauth.core.internal.httpkit import add_query_params
from allauth.idp.oidc.models import Client
from django import template
from django.conf import settings
from django.http import QueryDict
from django.urls import Resolver404, resolve
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _


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
def account_back_link(context):
    """Return the "Go back" link's URL and label across the account flow."""
    request = context["request"]
    destination = request.GET.get("next")
    session = getattr(request, "session", None)

    if _is_safe_destination(request, destination):
        if session is not None:
            session[RETURN_URL_SESSION_KEY] = destination
    else:
        if destination and session is not None:
            session.pop(RETURN_URL_SESSION_KEY, None)
        destination = session.get(RETURN_URL_SESSION_KEY) if session is not None else None
        if not _is_safe_destination(request, destination):
            if destination and session is not None:
                session.pop(RETURN_URL_SESSION_KEY, None)
            destination = None

    for url in filter(None, (destination, request.get_full_path())):
        parts = urlparse(url)
        if parts.netloc not in ("", request.get_host()):
            continue
        try:
            if resolve(parts.path).view_name != "idp:oidc:authorization":
                continue
        except Resolver404:
            continue
        params = QueryDict(parts.query)
        client = Client.objects.filter(id=params.get("client_id")).first()
        redirect_uri = params.get("redirect_uri")
        if client and redirect_uri in client.get_redirect_uris():
            cancel = {"error": "access_denied"}
            if params.get("state"):
                cancel["state"] = params["state"]
            return {
                "url": add_query_params(redirect_uri, cancel),
                "label": _("Go back to %(name)s") % {"name": client.name},
            }
        destination = None
        break

    if destination is None:
        destination = settings.WEB_CLIENT_URL

    host = urlparse(destination).netloc
    if host in ("", request.get_host(), urlparse(settings.WEB_CLIENT_URL).netloc):
        label = _("Go back to %(name)s") % {"name": "HydroServer"}
    else:
        label = _("Go back")

    return {"url": destination, "label": label}
