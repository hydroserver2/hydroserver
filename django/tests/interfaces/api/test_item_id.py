import pytest

from interfaces.api.collections import COLLECTIONS
from interfaces.api.schemas.base import ItemId, NewItemId
from tests.interfaces.api.helpers import API_PREFIX, api_operations

# Items identified by UUID share the id field of ItemId (responses) or NewItemId (bodies that create them), subclassed
# last so id is their first field. GeoJSON features take their id from it (OGC API - Features Core Req 39B).

ITEM_PATHS = {f"collections/{collection.id}/items/" for collection in COLLECTIONS}


def _subclasses(cls):
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _subclasses(subclass)


def _item_schemas():
    """The item schema of each collection's item GET operation, by collection item path."""

    for method, path, _, operation in api_operations():
        route = path.removeprefix(API_PREFIX)
        if method == "GET" and any(route.startswith(prefix) and route.count("/") == 3 for prefix in ITEM_PATHS):
            item_response = operation.response_models[200].model_fields["response"].annotation
            yield route, item_response.__pydantic_generic_metadata__["args"][0]


ITEM_SCHEMAS = list(_item_schemas())


def test_every_collection_item_get_is_found():
    assert len(ITEM_SCHEMAS) == len(COLLECTIONS)


@pytest.mark.parametrize("route, schema", ITEM_SCHEMAS, ids=[route for route, _ in ITEM_SCHEMAS])
def test_collection_items_are_identified_by_item_id(route, schema):
    assert issubclass(schema, ItemId)


@pytest.mark.parametrize("schema", [*_subclasses(ItemId), *_subclasses(NewItemId)], ids=lambda schema: schema.__name__)
def test_id_is_the_first_field(schema):
    if schema.__pydantic_generic_metadata__["origin"] is not None:
        schema = schema.__pydantic_generic_metadata__["origin"]

    assert next(iter(schema.model_fields)) == "id"


def test_ids_are_documented_once_for_every_schema(client):
    schemas = client.get("/api/ogc/openapi.json").json()["components"]["schemas"]

    assert schemas["UnitResponse"]["properties"]["id"]["description"] == "The item's unique identifier."
    assert list(schemas["UnitResponse"]["properties"])[0] == "id"
    assert schemas["UnitPostBody"]["properties"]["id"]["description"] == (
        "The new item's identifier. Generated if omitted."
    )
    assert "id" not in schemas["UnitPostBody"].get("required", [])
