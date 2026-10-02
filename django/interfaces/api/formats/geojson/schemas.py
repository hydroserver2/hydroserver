from typing import Any, Generic, Literal, Optional, TypeVar

from ninja import Schema
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from interfaces.api.http.links import Link

# GeoJSON response documents of OGC API - Features (Core Req 39), generic over the properties of their features.
# The models forbid extra members, so validating a response against them catches a member the response has but
# the documentation doesn't.

P = TypeVar("P")


class GeoJSONPoint(Schema):
    type: Literal["Point"]
    coordinates: tuple[float, float]

    model_config = ConfigDict(extra="forbid")


class GeoJSONFeature(Schema, Generic[P]):
    """A feature of a FeatureCollection."""

    type: Literal["Feature"]
    id: str
    geometry: Optional[GeoJSONPoint]
    properties: P

    model_config = ConfigDict(extra="forbid")


class GeoJSONFeatureDocument(GeoJSONFeature[P], Generic[P]):
    """A feature as a response document, with links and included resources as foreign members (Req 39C)."""

    links: list[Link]
    included: Optional[dict[str, list[Any]]] = None


class GeoJSONFeatureCollection(Schema, Generic[P]):
    type: Literal["FeatureCollection"]
    features: list[GeoJSONFeature[P]]
    number_matched: Optional[int] = None
    number_returned: int
    links: list[Link]
    included: Optional[dict[str, list[Any]]] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")
