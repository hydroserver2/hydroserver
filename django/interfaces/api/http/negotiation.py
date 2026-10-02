import inspect
import re

from functools import wraps
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponseBase
from django.utils.cache import patch_vary_headers
from ninja.errors import HttpError
from ninja.operation import Operation

from interfaces.api.collections import CollectionDefinition, get_collection
from interfaces.api.formats import Format, collection_formats
from interfaces.api.formats.profiles import Profile, collection_profiles, has_profiles, resolve_profile
from interfaces.api.http.errors import BadRequestError, NotAcceptableError

FORMAT_PARAM = "f"
PROFILE_PARAM = "profile"
ITEMS_PATH = re.compile(r"(?:^|/)collections/(?P<collection_id>[^/]+)/items(?P<item>/[^/]+)?/?$")


def items_collection(path: str) -> Optional[CollectionDefinition]:
    """The registered collection whose items or item the path addresses, if any."""

    match = ITEMS_PATH.search(path)

    return get_collection(match["collection_id"]) if match else None


def is_items_path(path: str) -> bool:
    """Whether the path addresses a collection's items rather than one item."""

    match = ITEMS_PATH.search(path)

    return match is not None and match["item"] is None


def profiles_path_collection(path: str) -> Optional[CollectionDefinition]:
    """
    The collection whose items the path addresses if the collection has profiles. Profiles vary pages of items,
    so they're negotiated for a collection's items, not for one item.
    """

    collection = items_collection(path)

    return collection if collection is not None and is_items_path(path) and has_profiles(collection) else None


def negotiated_query_params(request: HttpRequest) -> frozenset[str]:
    """The query parameters negotiate_format reads on the request rather than the view."""

    if not hasattr(request, "response_format"):
        return frozenset()

    return frozenset({FORMAT_PARAM, PROFILE_PARAM} if profiles_path_collection(request.path_info) else {FORMAT_PARAM})


def response_required_fields(request: HttpRequest) -> frozenset[str]:
    """The item fields the media type of the response's negotiated format requires, if any."""

    response_format = getattr(request, "response_format", None)
    collection = items_collection(request.path_info) if response_format is not None else None

    return response_format.required_fields(collection) if collection is not None else frozenset()


def negotiate(request: HttpRequest, collection: CollectionDefinition) -> Format:
    """
    Selects the response format from the f parameter, then the Accept header, then the collection's default.
    """

    formats = collection_formats(collection)

    if FORMAT_PARAM in request.GET:
        requested = request.GET[FORMAT_PARAM]
        selected = next((fmt for fmt in formats if fmt.key == requested), None)

        if selected is None:
            raise BadRequestError(
                f"Unsupported format '{requested}'. Allowed: {', '.join(fmt.key for fmt in formats)}."
            )

        return selected

    if not request.headers.get("Accept", "").strip():
        return formats[0]

    media_type = request.get_preferred_type([fmt.media_type for fmt in formats])

    if media_type is None:
        raise NotAcceptableError(
            "None of the media types in the Accept header are available. "
            f"Available: {', '.join(fmt.media_type for fmt in formats)}."
        )

    return next(fmt for fmt in formats if fmt.media_type == media_type)


def negotiate_profile(request: HttpRequest, collection: CollectionDefinition, fmt: Format) -> Optional[Profile]:
    """
    Selects the response profile: the first requested profile that the format supports for the collection.
    Requested profiles the format doesn't support are ignored rather than rejected, and without a profile
    the response is in the format's standard representation.
    """

    supported = collection_profiles(collection, fmt.key)
    if not supported:
        return None

    requested = [value.strip() for raw in request.GET.getlist(PROFILE_PARAM) for value in raw.split(",")]
    selected = (resolve_profile(value) for value in requested if value)

    return next((profile for profile in selected if profile in supported), None)


def negotiate_format(run: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    """
    Ninja view-mode decorator that negotiates the response format of GET requests to collection items, and the
    profile of requests to the items of collections with profiles. It stores them on the request as
    response_format, which create_response encodes the response with, and response_profile, which views shape
    the response by.

    Registered after reject_unknown_query_params, so it runs first, and a bad format is reported before
    authentication or query parameter validation.
    """

    operation = getattr(inspect.unwrap(run), "__self__", None)
    if not isinstance(operation, Operation):
        raise TypeError("negotiate_format must be registered with mode='view'.")

    @wraps(run)
    def wrapper(request: HttpRequest, **kwargs) -> HttpResponseBase:
        collection = items_collection(request.path_info) if request.method == "GET" else None

        if collection is None:
            return run(request, **kwargs)

        try:
            request.response_format = negotiate(request, collection)
        except HttpError as error:
            response = operation.api.create_response(request, {"message": error.message}, status=error.status_code)
            patch_vary_headers(response, ["Accept"])
            return response

        profiles_collection = profiles_path_collection(request.path_info)
        request.response_profile = (
            negotiate_profile(request, profiles_collection, request.response_format) if profiles_collection else None
        )

        return run(request, **kwargs)

    return wrapper
