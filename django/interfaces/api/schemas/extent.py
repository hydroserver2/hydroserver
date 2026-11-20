import math
import re

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any, Annotated
from ninja import Query, Schema
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

    parts = value.split(",") if isinstance(value, str) else list(value)

    if len(parts) == 1 and not str(parts[0]).strip():
        return None

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


# RFC 3339 section 5.6 date-time: a full date, "T", a time and a required UTC offset.
RFC3339_DATE_TIME = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})"
)


@dataclass(frozen=True)
class TimeInterval:
    """
    An OGC API datetime parameter value, per OGC API - Features - Part 1: Core. An instant has
    equal start and end; an interval may leave one end open (None).
    """

    start: Optional[datetime]
    end: Optional[datetime]


def parse_rfc3339(value: str) -> datetime:
    """Parses an RFC 3339 date-time, which requires a UTC offset, into an aware UTC datetime."""

    if not RFC3339_DATE_TIME.fullmatch(value):
        raise ValueError(
            f"Invalid date-time '{value}'. Use RFC 3339 with a UTC offset, e.g. 2024-01-01T00:00:00Z"
        )

    try:
        parsed = datetime.fromisoformat(value.upper())
    except ValueError:
        raise ValueError(f"Invalid date-time '{value}'")

    return parsed.astimezone(timezone.utc)


def parse_datetime(value: Any) -> Optional[TimeInterval]:
    """
    Parses an OGC API datetime query parameter value into a TimeInterval.

    Accepts an instant (date-time), a bounded interval (start/end) or a half-bounded interval
    whose open end is ".." or empty (../end, /end, start/.., start/), per Core Req 26.
    """

    if value is None or isinstance(value, TimeInterval):
        return value

    if not isinstance(value, str):
        raise ValueError("Datetime must be a string")

    value = value.strip()

    if "/" not in value:
        instant = parse_rfc3339(value)
        return TimeInterval(start=instant, end=instant)

    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError("Datetime interval must have exactly one '/' separating its start and end")

    start, end = (None if part in ("", "..") else parse_rfc3339(part) for part in parts)

    if start is None and end is None:
        raise ValueError("Datetime interval must have at least one bounded end")
    if start is not None and end is not None and start > end:
        raise ValueError("Datetime interval start must be earlier than or equal to its end")

    return TimeInterval(start=start, end=end)


DATETIME_JSON_SCHEMA = {
    "description": "Date-time or interval in RFC 3339 with a UTC offset: an instant "
    "(2024-01-01T00:00:00Z), a bounded interval (start/end), or a half-bounded interval with "
    "'..' or an empty value for the open end (../end, start/..). Items without a time match any "
    "datetime.",
    "type": "string",
    "style": "form",
    "explode": False,
}

DatetimeQuery = Annotated[
    Optional[TimeInterval],
    BeforeValidator(parse_datetime),
    WithJsonSchema(DATETIME_JSON_SCHEMA),
]


class ExtentQueryParameters(Schema):
    """
    Query parameters that filter items by their spatial and temporal extent, shared by every
    OGC API collection items endpoint.
    """

    bbox: BoundingBoxQuery = Query(None)
    datetime: DatetimeQuery = Query(None)
