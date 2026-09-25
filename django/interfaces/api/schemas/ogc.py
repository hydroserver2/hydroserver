from typing import Optional

from ninja import Schema
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from interfaces.api.http.links import Link


class CollectionResponse(Schema):
    """A collection's metadata (OGC API - Features Core collection.yaml)."""

    id: str
    title: str
    description: str
    item_type: Optional[str] = None
    links: list[Link]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class CollectionsResponse(Schema):
    """The collections the API serves (OGC API - Features Core collections.yaml)."""

    links: list[Link]
    collections: list[CollectionResponse]
