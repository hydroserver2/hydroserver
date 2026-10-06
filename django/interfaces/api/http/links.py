from typing import Optional
from urllib.parse import quote

from django.conf import settings
from django.http import HttpRequest
from django.urls import get_script_prefix, reverse
from ninja import Schema
from pydantic import SerializationInfo

from interfaces.api.formats import collection_formats
from interfaces.api.formats.profiles import collection_profiles
from interfaces.api.http.content_negotiation import FORMAT_PARAM, PROFILE_PARAM, items_route

JSON_MEDIA_TYPE = "application/json"


class Link(Schema):
    href: str
    rel: str
    type: Optional[str] = None
    title: Optional[str] = None


def api_root_path() -> str:
    """The OGC API root relative to Django's root, e.g., 'api/ogc/'."""

    return route_path("ogc:api-root")


def route_path(route_name: str) -> str:
    """A named route's path relative to Django's root, e.g., 'api/ogc/openapi.json'."""

    return reverse(route_name).removeprefix(get_script_prefix())


def build_absolute_url(path: str, query_string: str = "") -> str:
    """Builds an absolute URL for a path relative to Django's root from PROXY_BASE_URL"""

    url = settings.PROXY_BASE_URL.rstrip("/") + "/" + path.lstrip("/")

    return f"{url}?{query_string}" if query_string else url


def build_api_url(path: str = "") -> str:
    """Builds an absolute URL for a path relative to the OGC API root, e.g. 'collections/units'."""

    return build_absolute_url(api_root_path() + path.lstrip("/"))


def implied_format_key(request: HttpRequest) -> Optional[str]:
    """
    The f value that links to this response document needs beyond the request's own query string: the
    negotiated format's key when the Accept header, not f, selected a format other than the default. Links
    to the default format leave f out, so their hrefs are the collection's canonical URLs.
    """

    response_format = getattr(request, "response_format", None)
    if response_format is None or FORMAT_PARAM in request.GET:
        return None

    collection = getattr(request, "response_collection", None)

    return response_format.key if collection is not None and response_format.key != collection.default_format else None


def response_media_type(request: HttpRequest) -> str:
    """The media type of this response document."""

    response_format = getattr(request, "response_format", None)

    return response_format.media_type if response_format is not None else JSON_MEDIA_TYPE


def build_self_link(request: HttpRequest, path: Optional[str] = None) -> Link:
    """Builds a link to this response document."""

    if path:
        return Link(href=build_absolute_url(path), rel="self", type=JSON_MEDIA_TYPE)

    query_string = request.META.get("QUERY_STRING", "")
    format_key = implied_format_key(request)
    if format_key is not None:
        query_string = "&".join(part for part in (query_string, f"{FORMAT_PARAM}={format_key}") if part)

    return Link(
        href=build_absolute_url(request.path_info, query_string), rel="self", type=response_media_type(request)
    )


def build_alternate_links(request: HttpRequest) -> list[Link]:
    """Builds a link to this response document in every other format its collection serves."""

    response_format = getattr(request, "response_format", None)
    collection = getattr(request, "response_collection", None)

    if response_format is None or collection is None:
        return []

    links = []
    for fmt in collection_formats(collection):
        if fmt.key == response_format.key:
            continue

        query = request.GET.copy()
        query[FORMAT_PARAM] = fmt.key

        response_profile = getattr(request, "response_profile", None)
        if response_profile is None or response_profile not in collection_profiles(collection, fmt.key):
            query.pop(PROFILE_PARAM, None)

        links.append(
            Link(href=build_absolute_url(request.path_info, query.urlencode()), rel="alternate", type=fmt.media_type)
        )

    return links


def build_collection_link(request: HttpRequest) -> Optional[Link]:
    """Builds a link to the collection that contains the requested item."""

    route = items_route(request.path_info)

    if route is None or not route.is_item:
        return None

    return Link(
        href=build_api_url(f"collections/{route.collection.id}"),
        rel="collection",
        type=JSON_MEDIA_TYPE,
    )


def build_page_link(request: HttpRequest, rel: str, offset: int, limit: int) -> Link:
    """Builds a pagination link with the specified parameters."""

    query = request.GET.copy()
    query["offset"] = str(offset)
    query["limit"] = str(limit)

    format_key = implied_format_key(request)
    if format_key is not None:
        query[FORMAT_PARAM] = format_key

    return Link(
        href=build_absolute_url(request.path_info, query.urlencode()), rel=rel, type=response_media_type(request)
    )


def build_profile_link(request: HttpRequest) -> Optional[Link]:
    """
    Builds a link to the profile this response document is in.
    """

    response_profile = getattr(request, "response_profile", None)
    if response_profile is None:
        return None

    return Link(href=response_profile.uri, rel="profile", title=response_profile.title)


def build_page_links(request: HttpRequest, offset: int, limit: int, returned: int) -> list[Link]:
    """
    Returns the self-link, links to the page in other formats, the profile link, and next and prev links for a page
    of results.
    """

    profile_link = build_profile_link(request)
    links = [build_self_link(request), *build_alternate_links(request), *([profile_link] if profile_link else [])]

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


def quoted_string(value: str) -> str:
    """Quotes a header parameter value, escaping backslashes and double quotes."""

    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def link_header(links: list[dict]) -> str:
    """
    Serializes links as the value of an RFC 8288 Link header. Header values must be ASCII, so non-ASCII titles are
    sent as title* in RFC 8187 encoding. Hrefs are percent-encoded URLs.
    """

    def link_value(link: dict) -> str:
        params = [f"rel={quoted_string(link['rel'])}"]

        if link.get("type"):
            params.append(f"type={quoted_string(link['type'])}")
        if link.get("title"):
            title = link["title"]
            if title.isascii():
                params.append(f"title={quoted_string(title)}")
            else:
                params.append(f"title*=UTF-8''{quote(title, safe='')}")

        return f"<{link['href']}>; " + "; ".join(params)

    return ", ".join(link_value(link) for link in links)
