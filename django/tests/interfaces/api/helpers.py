from dataclasses import replace
from typing import Iterator, NamedTuple
from urllib.parse import parse_qs, urlsplit

import orjson

from ninja.operation import Operation

from interfaces.api import collections
from interfaces.api.collections import _COLLECTIONS_BY_ID
from interfaces.api.urls import api
from interfaces.api.views import ogc

# Helpers shared by the API tests. Fixtures live in conftest.py; plain functions and constants live here, so tests
# import them rather than importing from conftest.

API_PREFIX = "/api/ogc/"

# The PROXY_BASE_URL the proxy_base_url fixture sets. Links are built from it, not the request's Host, which the test
# client sends as "testserver".
BASE_URL = "https://hydroserver.example.org"


def _body(response_or_body) -> dict:
    return response_or_body if isinstance(response_or_body, dict) else orjson.loads(response_or_body.content)


def links_by_rel(response_or_body) -> dict[str, dict]:
    """A response document's links by relation type; for a repeated relation type, the last link."""

    return {link["rel"]: link for link in _body(response_or_body)["links"]}


def links_with_rel(response_or_body, rel: str) -> list[dict]:
    """A response document's links with the relation type, in order."""

    return [link for link in _body(response_or_body)["links"] if link["rel"] == rel]


def query_params(href: str) -> dict[str, list[str]]:
    """A link's query parameters, each with its list of values."""

    return parse_qs(urlsplit(href).query)


def query_values(href: str) -> dict[str, str]:
    """A link's query parameters, each with its first value."""

    return {key: values[0] for key, values in query_params(href).items()}


class ApiOperation(NamedTuple):
    method: str
    # OpenAPI-style path, e.g., /api/ogc/collections/units/items/{unit_id}
    path: str
    # The prefix of the router the operation is mounted on, e.g., collections/units
    router_prefix: str
    operation: Operation


def api_operations() -> Iterator[ApiOperation]:
    """Every operation of the API, once per HTTP method."""

    for bound_router in api._get_bound_routers():
        router_prefix = bound_router.prefix.strip("/")
        for path, path_view in bound_router.path_operations.items():
            route = "/".join(part.strip("/") for part in (bound_router.prefix, path) if part.strip("/"))
            for operation in path_view.operations:
                for method in operation.methods:
                    yield ApiOperation(method, f"{API_PREFIX}{route}", router_prefix, operation)


def set_collection_formats(monkeypatch, collection_ids, formats):
    """
    Replaces the formats of the given collections everywhere the registry is read. formats maps format keys to
    profile keys, as CollectionDefinition.formats does.
    """

    registry = tuple(
        replace(collection, formats=formats) if collection.id in collection_ids else collection
        for collection in collections.COLLECTIONS
    )

    for module in (collections, ogc):
        monkeypatch.setattr(module, "COLLECTIONS", registry)
    for collection in registry:
        monkeypatch.setitem(_COLLECTIONS_BY_ID, collection.id, collection)
