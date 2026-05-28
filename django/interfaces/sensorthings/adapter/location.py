from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.types import Absent
from core.sta.models import Location
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, LocationDTO
from .utils import SensorThingsUtils


_GROUP_BY_PARTITION = {
    "thing": "thing_id",
    "things": "thing_id",
}


class LocationMixin(SensorThingsUtils):

    def get_locations(self, filters=None, orderby=None, group_by=None, select=None,
                      top=100, skip=0, count=False, context=None):
        needs_properties = select is None or "properties" in select

        locations = Location.objects
        if needs_properties:
            locations = locations.select_related("thing__workspace")
        locations = locations.visible(principal=context.principal if context else None)

        if filters:
            locations = self.apply_filters(locations, Location, filters)
        if orderby:
            locations = self.apply_order(locations, Location, orderby)
        locations = locations.distinct()

        if group_by and group_by[0] == "location":
            locations = locations.filter(pk__in=group_by[1])
            loc_list = list(locations)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[location.id for location in loc_list])
            }
        elif group_by and (partition_field := _GROUP_BY_PARTITION.get(group_by[0])):
            locations = locations.filter(**{f"{partition_field}__in": group_by[1]})
            loc_list = list(self.apply_window(locations, partition_field, top, skip))
            groups = {}
            for loc in loc_list:
                groups.setdefault(getattr(loc, partition_field), []).append(loc.id)
            collections = {
                thing_id: CollectionDTO(
                    entity_count=(1 if groups.get(thing_id) else 0) if count else None,
                    entity_ids=groups.get(thing_id, []),
                )
                for thing_id in group_by[1]
            }
        else:
            entity_count = locations.count() if count else None
            loc_list = list(self.apply_pagination(locations, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[location.id for location in loc_list],
                )
            }

        try:
            entities = {
                location.id: LocationDTO(
                    id=self.select_field(select, "id", location.id),
                    name=self.select_field(select, "name", location.name),
                    description=self.select_field(select, "description", location.description),
                    encoding_type="application/geo+json",
                    location=(
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [location.longitude, location.latitude],
                            },
                        }
                        if select is None or "location" in select else Absent
                    ),
                    properties=(
                        {
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
                        }
                        if needs_properties else Absent
                    ),
                    thing_ids=[location.thing_id],
                )
                for location in loc_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_locations(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
