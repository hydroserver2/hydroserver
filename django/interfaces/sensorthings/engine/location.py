from typing import Optional
from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from domains.sta.models import Location
from sensorthings.components.locations.engine import LocationBaseEngine
from sensorthings.components.locations.schemas import (
    Location as LocationSchema,
    LocationPostBody,
    LocationPatchBody,
)
from .utils import SensorThingsUtils


class LocationEngine(LocationBaseEngine, SensorThingsUtils):
    def get_locations(
        self,
        location_ids: Optional[list[str]] = None,
        thing_ids: Optional[list[str]] = None,
        pagination: Optional[dict] = None,
        ordering: Optional[dict] = None,
        filters: Optional[dict] = None,
        expanded: bool = False,
        get_count: bool = False,
    ) -> (list[dict], int):

        if location_ids:
            location_ids = self.strings_to_uuids(location_ids)

        if thing_ids:
            thing_ids = self.strings_to_uuids(thing_ids)

        locations = Location.objects

        if location_ids:
            locations = locations.filter(id__in=location_ids)

        if thing_ids:
            locations = locations.filter(thing_id__in=thing_ids)

        locations = locations.visible(principal=self.request.principal)  # noqa

        if filters:
            locations = self.apply_filters(
                queryset=locations, component=LocationSchema, filters=filters
            )

        if ordering:
            locations = self.apply_order(
                queryset=locations, component=LocationSchema, order_by=ordering
            )

        locations = locations.distinct()

        if get_count:
            count = locations.count()
        else:
            count = None

        if pagination:
            locations = self.apply_pagination(
                queryset=locations,
                top=pagination.get("top"),
                skip=pagination.get("skip"),
            )

        try:
            return {
                location.id: {
                    "id": location.id,
                    "name": location.name,
                    "description": location.description,
                    "encoding_type": location.encoding_type,
                    "location": {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [location.longitude, location.latitude],
                        },
                    },
                    "properties": {
                        "elevation_m": location.elevation_m,
                        "elevation_datum": location.elevation_datum,
                        "admin_area_1": location.admin_area_1,
                        "admin_area_2": location.admin_area_2,
                        "country": location.country,
                        "workspace": {
                            "id": location.thing.workspace.id,
                            "name": location.thing.workspace.name,
                            "link": location.thing.workspace.link,
                            "is_private": location.thing.workspace.is_private,
                        },
                    },
                    "thing_ids": [location.thing_id],
                }
                for location in locations
            }, count
        except (
            DatabaseError,
            DataError,
        ) as e:
            raise HttpError(400, str(e))

    def create_location(self, location: LocationPostBody) -> str:
        raise HttpError(403, "You do not have permission to perform this action.")

    def update_location(self, location_id: str, location: LocationPatchBody) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")

    def delete_location(self, location_id: str) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")
