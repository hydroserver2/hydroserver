from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from django.urls import get_script_prefix, reverse
from ninja import Schema
from pydantic import SerializationInfo

JSON_MEDIA_TYPE = "application/json"


class Link(Schema):
    href: str
    rel: str
    type: str
    title: Optional[str] = None


def build_absolute_url(path: str) -> str:
    """
    Builds an absolute URL for a path relative to Django's root from PROXY_BASE_URL, which is the
    public URL of Django's root, so links are correct behind a proxy regardless of the request's
    Host.
    """

    return settings.PROXY_BASE_URL.rstrip("/") + "/" + path.lstrip("/")


def build_api_url(path: str = "") -> str:
    """Builds an absolute URL for a path relative to the OGC API root, e.g. 'collections/units'."""

    api_root = reverse("ogc:api-root").removeprefix(get_script_prefix())

    return build_absolute_url(api_root + path.lstrip("/"))


def build_url(request: HttpRequest, query_string: str) -> str:
    """Builds an absolute URL for the request's path with the given query string."""

    url = build_absolute_url(request.path_info)

    return f"{url}?{query_string}" if query_string else url


def build_self_link(request: HttpRequest) -> Link:
    """A link to this response document (OGC API - Features Core Req 28 and 35)."""

    return Link(
        href=build_url(request, request.META.get("QUERY_STRING", "")),
        rel="self",
        type=JSON_MEDIA_TYPE,
    )


def build_page_link(request: HttpRequest, rel: str, offset: int, limit: int) -> Link:
    query = request.GET.copy()
    query["offset"] = str(offset)
    query["limit"] = str(limit)

    return Link(href=build_url(request, query.urlencode()), rel=rel, type=JSON_MEDIA_TYPE)


def build_page_links(request: HttpRequest, offset: int, limit: int, returned: int) -> list[Link]:
    """
    Returns the self-link plus next and prev links for a page of results (OGC API - Features
    Core Req 28, Recs 17-19 and Permission 7).

    A next link is included when the page is full rather than by comparing against the total
    count, which can be a Postgres estimate or a stored value count that runs low. At worst the
    last next link leads to an empty page, which Core allows.
    """

    links = [build_self_link(request)]

    if limit <= 0:
        return links

    if returned >= limit:
        links.append(build_page_link(request, "next", offset + limit, limit))

    if offset > 0:
        links.append(build_page_link(request, "prev", max(0, offset - limit), limit))

    return links


def get_request(info: SerializationInfo) -> Optional[HttpRequest]:
    """Returns the request Ninja passes in the serialization context, if any."""

    return (info.context or {}).get("request") if info.context else None
