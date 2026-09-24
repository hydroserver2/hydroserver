import math

from dataclasses import dataclass
from typing import Optional, Any, Annotated
from pydantic import BeforeValidator, WithJsonSchema


@dataclass(frozen=True)
class BoundingBox:
    """
    A WGS 84 longitude/latitude (CRS84) bounding box, per OGC API - Features - Part 1: Core.

    A west edge greater than the east edge describes a box that crosses the antimeridian.
    """

    west: float
    south: float
    east: float
    north: float

    @property
    def crosses_antimeridian(self) -> bool:
        return self.west > self.east

    def contains(self, longitude: float, latitude: float) -> bool:
        """Returns whether a point lies inside the box, boundaries included."""

        if not self.south <= latitude <= self.north:
            return False

        if self.crosses_antimeridian:
            return longitude >= self.west or longitude <= self.east

        return self.west <= longitude <= self.east


def parse_bbox(value: Any) -> Optional[BoundingBox]:
    """
    Parses an OGC API bbox query parameter value into a BoundingBox.

    Accepts four numbers (min lon, min lat, max lon, max lat) or six numbers
    (min lon, min lat, min height, max lon, max lat, max height). HydroServer geometries
    are two-dimensional, so the height range of a six-number box is validated but not
    used for filtering.
    """

    if value is None or isinstance(value, BoundingBox):
        return value

    if isinstance(value, str) and value.strip().lower() == "null":
        return None

    parts = value.split(",") if isinstance(value, str) else list(value)

    try:
        numbers = [float(part) for part in parts]
    except (TypeError, ValueError):
        raise ValueError("Bounding box must contain only numeric values")

    if not all(math.isfinite(number) for number in numbers):
        raise ValueError("Bounding box must contain only finite numeric values")

    if len(numbers) == 4:
        west, south, east, north = numbers
    elif len(numbers) == 6:
        west, south, min_height, east, north, max_height = numbers
        if min_height > max_height:
            raise ValueError("Bounding box minimum height must be less than or equal to maximum height")
    else:
        raise ValueError(
            "Bounding box must have 4 or 6 comma-separated values: "
            "min_lon,min_lat,max_lon,max_lat or min_lon,min_lat,min_height,max_lon,max_lat,max_height"
        )

    if not all(-180 <= longitude <= 180 for longitude in (west, east)):
        raise ValueError("Bounding box longitudes must be between -180 and 180")
    if not all(-90 <= latitude <= 90 for latitude in (south, north)):
        raise ValueError("Bounding box latitudes must be between -90 and 90")
    if south > north:
        raise ValueError("Bounding box minimum latitude must be less than or equal to maximum latitude")

    return BoundingBox(west=west, south=south, east=east, north=north)


BBOX_JSON_SCHEMA = {
    "description": "Bounding box in WGS 84 longitude/latitude: min_lon,min_lat,max_lon,max_lat, "
    "or six values including min and max heights (heights are not used for filtering). A min_lon "
    "greater than max_lon crosses the antimeridian. Items without a location match any bounding box.",
    "type": "array",
    "oneOf": [{"minItems": 4, "maxItems": 4}, {"minItems": 6, "maxItems": 6}],
    "items": {"type": "number"},
    "style": "form",
    "explode": False,
}

BoundingBoxQuery = Annotated[
    Optional[BoundingBox],
    BeforeValidator(parse_bbox),
    WithJsonSchema(BBOX_JSON_SCHEMA),
]
