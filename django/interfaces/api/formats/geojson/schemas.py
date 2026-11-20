from typing import Annotated, Any, Generic, Literal, Optional, TypeVar, Union

from ninja import Schema
from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from interfaces.api.http.links import Link


P = TypeVar("P")


class GeoJSONPoint(Schema):
    type: Literal["Point"]
    coordinates: tuple[float, float]

    model_config = ConfigDict(extra="forbid")


class GeoJSONPolygon(Schema):
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]

    model_config = ConfigDict(extra="forbid")


GeoJSONGeometry = Annotated[Union[GeoJSONPoint, GeoJSONPolygon], Field(discriminator="type")]


class GeoJSONFeature(Schema, Generic[P]):
    """A feature of a FeatureCollection."""

    type: Literal["Feature"]
    id: str
    geometry: Optional[GeoJSONGeometry]
    bbox: Optional[list[float]] = Field(None, min_length=4, max_length=4)
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
