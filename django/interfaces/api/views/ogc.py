from ninja import Router, Path

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.collections import COLLECTIONS, CollectionDefinition, get_collection
from interfaces.api.http.errors import NotFoundError
from interfaces.api.http.links import JSON_MEDIA_TYPE, Link, build_api_url, build_self_link
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas.ogc import CollectionResponse, CollectionsResponse

ogc_router = Router(tags=["Collections"])


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
            Link(href=f"{collection_url}/items", rel="items", type=JSON_MEDIA_TYPE),
        ],
    )


@ogc_router.get(
    "/collections",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={200: CollectionsResponse},
    by_alias=True,
    exclude_none=True,
)
def get_collections(request: HydroServerHttpRequest):
    """
    Get the collections the API serves.
    """

    return 200, CollectionsResponse(
        links=[build_self_link(request)],
        collections=[build_collection(collection) for collection in COLLECTIONS],
    )


@ogc_router.get(
    "/collections/{collection_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={200: CollectionResponse, 404: str},
    by_alias=True,
    exclude_none=True,
)
def get_collection_metadata(request: HydroServerHttpRequest, collection_id: Path[str]):
    """
    Get a collection.
    """

    collection = get_collection(collection_id)
    if collection is None:
        raise NotFoundError(f"Collection '{collection_id}' does not exist")

    return 200, build_collection(collection)
