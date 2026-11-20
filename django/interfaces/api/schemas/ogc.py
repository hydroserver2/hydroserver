from ninja import Schema
from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from interfaces.api.collections import ItemType
from interfaces.api.http.links import Link


class CollectionResponse(Schema):
    """A collection's metadata (OGC API - Features Core collection.yaml)."""

    id: str
    title: str
    description: str
    item_type: ItemType = Field(
        ...,
        description="The type of the collection's items: 'feature' for spatial items served as "
        "OGC API features, or 'resource' for non-spatial items.",
    )
    links: list[Link]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class CollectionsResponse(Schema):
    """The collections the API serves (OGC API - Features Core collections.yaml)."""

    links: list[Link]
    collections: list[CollectionResponse]


class LandingPageResponse(Schema):
    """The API's landing page (OGC API - Features Core landingPage.yaml)."""

    title: str
    description: str
    links: list[Link]


class ConformanceResponse(Schema):
    """The conformance classes the API implements (OGC API - Features Core confClasses.yaml)."""

    conforms_to: list[str]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
