import re

from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from django.urls import get_script_prefix, reverse
from ninja import Schema
from pydantic import SerializationInfo

from interfaces.api.collections import get_collection

JSON_MEDIA_TYPE = "application/json"
COLLECTION_ITEM_PATH = re.compile(r"collections/(?P<collection_id>[^/]+)/items/[^/]+")


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


def route_path(route_name: str) -> str:
    """A named route's path relative to Django's root, e.g. 'api/ogc/openapi.json'."""

    return reverse(route_name).removeprefix(get_script_prefix())


def api_root_path() -> str:
    """The OGC API root relative to Django's root, e.g. 'api/ogc/'."""

    return route_path("ogc:api-root")


def build_api_url(path: str = "") -> str:
    """Builds an absolute URL for a path relative to the OGC API root, e.g. 'collections/units'."""

    return build_absolute_url(api_root_path() + path.lstrip("/"))


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


def build_collection_link(request: HttpRequest) -> Optional[Link]:
    """
    A link to the collection that contains the requested item (OGC API - Features Core Req 35),
    or None when the request isn't for /collections/{collectionId}/items/{itemId}, such as a
    nested sub-resource whose parent isn't a collection.
    """

    path = request.path_info.lstrip("/").removeprefix(api_root_path())
    match = COLLECTION_ITEM_PATH.fullmatch(path)

    if match is None or get_collection(match["collection_id"]) is None:
        return None

    return Link(
        href=build_api_url(f"collections/{match['collection_id']}"),
        rel="collection",
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
