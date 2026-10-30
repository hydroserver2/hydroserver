from ninja import Router, Path

from interfaces.api.collections import DOCS_URL, COLLECTIONS, CollectionDefinition, get_collection, openapi_tag
from interfaces.api.http.errors import NotFoundError
from interfaces.api.formats import collection_formats, formats_conformance
from interfaces.api.formats.profiles import profiles_conformance
from interfaces.api.http.content_negotiation import FORMAT_PARAM
from interfaces.api.http.links import (
    JSON_MEDIA_TYPE,
    Link,
    build_absolute_url,
    build_api_url,
    build_self_link,
    route_path,
)
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas.ogc import (
    CollectionResponse,
    CollectionsResponse,
    ConformanceResponse,
    LandingPageResponse,
)

API_TITLE = "HydroServer Data Management API"
API_DESCRIPTION = (
    "Provides access to hydrologic monitoring sites, datastreams, and observations managed in HydroServer."
)

# The OpenAPI document's description, in Markdown. The landing page keeps the short API_DESCRIPTION.
API_DOCUMENTATION = f"""
HydroServer's primary API for creating, managing, and retrieving hydrologic data and metadata: workspaces and
their access control, monitoring sites, datastreams, and observations, the metadata and controlled vocabularies
that describe them, and the Job Orchestration System tasks that load, derive, and monitor data.

The API implements [OGC API - Features](https://ogcapi.ogc.org/features/). Each type of resource is a
collection listed at `/collections`, with its items at `/collections/{{collectionId}}/items`, and `/conformance`
lists the standards the API conforms to.

## Additional Documentation

- [Using the Data Management API]({DOCS_URL}/user-guides/how-to/using-the-data-management-api): paging,
  filtering, response formats, creating, updating, and deleting items, and errors, with examples
- [Authenticating]({DOCS_URL}/references/hydroserver-apis#authenticating) with API keys, OIDC access tokens,
  email and password, or browser sessions
- [Data model]({DOCS_URL}/references/data-model) and [data dictionary]({DOCS_URL}/references/data-dictionary)
- [HydroServer APIs]({DOCS_URL}/references/hydroserver-apis), including HydroServer's SensorThings API
""".strip()

# Tags of the operations that describe the API itself, which come before the collections' tags.
CAPABILITY_TAGS = (
    openapi_tag(
        "Capabilities",
        "The API's landing page and conformance declaration.",
        "/user-guides/how-to/using-the-data-management-api#exploring-the-api",
    ),
    openapi_tag(
        "Collections",
        "The collections the API serves, one for each type of resource.",
        "/user-guides/how-to/using-the-data-management-api#exploring-the-api",
    ),
)

CORE_CONFORMANCE_CLASSES = (
    "http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/landing-page",
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
)

PROPERTY_SELECTION_CONFORMANCE_CLASSES = (
    "http://www.opengis.net/spec/ogcapi-features-6/1.0/conf/properties",
    "http://www.opengis.net/spec/ogcapi-features-6/1.0/conf/properties-features",
)

ogc_router = Router(tags=["Collections"])


@ogc_router.get(
    "",
    response={200: LandingPageResponse},
    by_alias=True,
    exclude_none=True,
    tags=["Capabilities"],
)
def get_landing_page(request: HydroServerHttpRequest):
    """
    Get the API's landing page, which links to the API definition, conformance declaration, and
    collections.
    """

    return 200, LandingPageResponse(
        title=API_TITLE,
        description=API_DESCRIPTION,
        links=[
            build_self_link(request),
            Link(
                href=build_absolute_url(route_path("ogc:openapi-json")),
                rel="service-desc",
                type=JSON_MEDIA_TYPE,
                title="The API definition",
            ),
            Link(
                href=build_absolute_url(route_path("ogc:openapi-view")),
                rel="service-doc",
                type="text/html",
                title="The API documentation",
            ),
            Link(
                href=build_api_url("conformance"),
                rel="conformance",
                type=JSON_MEDIA_TYPE,
                title="OGC API conformance classes implemented by this server",
            ),
            Link(
                href=build_api_url("conformance"),
                rel="http://www.opengis.net/def/rel/ogc/1.0/conformance",
                type=JSON_MEDIA_TYPE,
                title="OGC API conformance classes implemented by this server",
            ),
            Link(
                href=build_api_url("collections"),
                rel="data",
                type=JSON_MEDIA_TYPE,
                title="Information about the collections",
            ),
        ],
    )


@ogc_router.get(
    "/conformance",
    response={200: ConformanceResponse},
    by_alias=True,
    tags=["Capabilities"],
)
def get_conformance(request: HydroServerHttpRequest):
    """
    Get the OGC API conformance classes the API implements.
    """

    conforms_to = [
        *CORE_CONFORMANCE_CLASSES,
        *formats_conformance(COLLECTIONS),
        *profiles_conformance(COLLECTIONS),
        *PROPERTY_SELECTION_CONFORMANCE_CLASSES,
    ]

    return 200, ConformanceResponse(conforms_to=conforms_to)


def build_collection(collection: CollectionDefinition) -> CollectionResponse:
    """
    Builds a collection's metadata. Both /collections and /collections/{collectionId} use it, so
    the two stay identical (OGC API - Features Core Req 19).
    """

    collection_url = build_api_url(f"collections/{collection.id}")

    return CollectionResponse(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        item_type=collection.item_type,
        links=[
            Link(href=collection_url, rel="self", type=JSON_MEDIA_TYPE),
            *build_items_links(collection, collection_url),
        ],
    )


def build_items_links(collection: CollectionDefinition, collection_url: str) -> list[Link]:
    """
    Builds a link to the collection's items in each format it serves, the default first and without an f
    parameter.
    """

    return [
        Link(
            href=f"{collection_url}/items" if index == 0 else f"{collection_url}/items?{FORMAT_PARAM}={fmt.key}",
            rel="items",
            type=fmt.media_type,
        )
        for index, fmt in enumerate(collection_formats(collection))
    ]


@ogc_router.get(
    "/collections",
    response={200: CollectionsResponse},
    by_alias=True,
    exclude_none=True,
)
def get_collections(request: HydroServerHttpRequest):
    """
    Get the collections the API serves, with links to each collection's items in the formats
    they're available in.
    """

    return 200, CollectionsResponse(
        links=[build_self_link(request)],
        collections=[build_collection(collection) for collection in COLLECTIONS],
    )


@ogc_router.get(
    "/collections/{collection_id}",
    response={200: CollectionResponse, 404: str},
    by_alias=True,
    exclude_none=True,
)
def get_collection_metadata(request: HydroServerHttpRequest, collection_id: Path[str]):
    """
    Get a collection's description and links.
    """

    collection = get_collection(collection_id)
    if collection is None:
        raise NotFoundError(f"Collection '{collection_id}' does not exist")

    return 200, build_collection(collection)
