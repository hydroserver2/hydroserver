from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.types import Absent
from core.sta.models import Thing, Location
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, ThingDTO
from .utils import SensorThingsUtils


_GROUP_BY_PARTITION = {
    "location": "locations__id",
    "locations": "locations__id",
}


class ThingMixin(SensorThingsUtils):

    def get_things(self, filters=None, orderby=None, group_by=None, select=None,
                   top=100, skip=0, count=False, context=None):
        needs_properties = select is None or "properties" in select

        things = Thing.objects
        if needs_properties:
            things = things.select_related("workspace").prefetch_related(
                "thing_file_attachments", "thing_tags"
            )
        things = things.prefetch_related("locations").visible(
            principal=context.principal if context else None
        )

        if filters:
            things = self.apply_filters(things, Thing, filters)
        if orderby:
            things = self.apply_order(things, Thing, orderby)
        things = things.distinct()

        if group_by and group_by[0] == "thing":
            things = things.filter(pk__in=group_by[1])
            thing_list = list(things)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[thing.id for thing in thing_list])
            }
        elif group_by and (partition_field := _GROUP_BY_PARTITION.get(group_by[0])):
            things = things.filter(**{f"{partition_field}__in": group_by[1]})
            thing_list = list(things)
            thing_ids = {thing.id for thing in thing_list}
            loc_to_thing = dict(
                Location.objects.filter(id__in=group_by[1]).values_list("id", "thing_id")
            )
            collections = {
                loc_id: CollectionDTO(
                    entity_count=(1 if thing_id in thing_ids else 0) if count else None,
                    entity_ids=[thing_id] if thing_id in thing_ids else [],
                )
                for loc_id, thing_id in loc_to_thing.items()
            }
        else:
            entity_count = things.count() if count else None
            thing_list = list(self.apply_pagination(things, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[thing.id for thing in thing_list],
                )
            }

        try:
            entities = {
                thing.id: ThingDTO(
                    id=self.select_field(select, "id", thing.id),
                    name=self.select_field(select, "name", thing.name),
                    description=self.select_field(select, "description", thing.description),
                    properties=(
                        {
                            "sampling_feature_type": thing.sampling_feature_type,
                            "sampling_feature_code": thing.sampling_feature_code,
                            "site_type": thing.site_type,
                            "data_disclaimer": thing.data_disclaimer,
                            "is_private": thing.is_private,
                            "workspace": {
                                "id": thing.workspace.id,
                                "name": thing.workspace.name,
                                "link": thing.workspace.link,
                                "is_private": thing.workspace.is_private,
                            },
                            "tags": {tag.key: tag.value for tag in thing.thing_tags.all()},
                            "file_attachments": {
                                fa.name: fa.link
                                for fa in thing.thing_file_attachments.all()
                            },
                        }
                        if needs_properties else Absent
                    ),
                    location_ids=[loc.id for loc in thing.locations.all()],
                )
                for thing in thing_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_things(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_things(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_things(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
