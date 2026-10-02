from dataclasses import dataclass
from typing import Any, Optional

from django.http import HttpRequest


@dataclass(frozen=True)
class ResolvedGeometry:
    """A feature's GeoJSON geometry and, for geometries with an extent, its bbox member (RFC 7946, Section 5)."""

    geometry: Optional[dict]
    bbox: Optional[list[float]] = None


NO_GEOMETRY = ResolvedGeometry(None)


class GeometrySource:
    """Where a collection's features get their geometry from."""

    fields: tuple[str, ...] = ()
    geometry_fields: tuple[str, ...] = ()

    def resolve(self, items: list[dict], request: HttpRequest) -> list[ResolvedGeometry]:
        """The geometry of each item, in order."""

        raise NotImplementedError


@dataclass(frozen=True)
class PointGeometry(GeometrySource):
    """A point built from two of the item's own fields, e.g. a monitoring site's latitude and longitude."""

    longitude: str = "longitude"
    latitude: str = "latitude"

    @property
    def fields(self) -> tuple[str, ...]:
        return self.longitude, self.latitude

    @property
    def geometry_fields(self) -> tuple[str, ...]:
        return self.fields

    def resolve(self, items: list[dict], request: HttpRequest) -> list[ResolvedGeometry]:
        return [
            point(item[self.longitude], item[self.latitude])
            if item.get(self.longitude) is not None and item.get(self.latitude) is not None
            else NO_GEOMETRY
            for item in items
        ]


@dataclass(frozen=True)
class SiteExtent(GeometrySource):
    """
    The extent of the monitoring sites a workspace holds that the requester can view: a polygon with a bbox
    member, a point when the sites share one location, or no geometry without any. The extent is a plain
    longitude/latitude box, so sites on both sides of the antimeridian give a box spanning the other way round.
    """

    fields: tuple[str, ...] = ("id",)

    def resolve(self, items: list[dict], request: HttpRequest) -> list[ResolvedGeometry]:
        from django.db.models import Max, Min
        from core.sta.models import MonitoringSite

        visible_sites = request.principal.filter_by_permission(
            MonitoringSite.objects.filter(workspace_id__in=[item["id"] for item in items]), "can_view"
        )
        extents = {
            str(row["workspace_id"]): row
            for row in visible_sites.values("workspace_id").annotate(
                west=Min("longitude"), south=Min("latitude"), east=Max("longitude"), north=Max("latitude")
            )
        }

        return [extent(extents[str(item["id"])]) if str(item["id"]) in extents else NO_GEOMETRY for item in items]


def point(longitude: Any, latitude: Any) -> ResolvedGeometry:
    return ResolvedGeometry({"type": "Point", "coordinates": [float(longitude), float(latitude)]})


def extent(row: dict) -> ResolvedGeometry:
    """A box as a polygon with a bbox member, or as a point when it has no width or height."""

    west, south, east, north = (float(row[edge]) for edge in ("west", "south", "east", "north"))

    if west == east and south == north:
        return point(west, south)

    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]

    return ResolvedGeometry({"type": "Polygon", "coordinates": [ring]}, bbox=[west, south, east, north])
