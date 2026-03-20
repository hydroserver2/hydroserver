from uuid import UUID
from typing import Optional
from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from domains.sta.models import Thing
from sensorthings.components.things.engine import ThingBaseEngine
from sensorthings.components.things.schemas import Thing as ThingSchema
from .utils import SensorThingsUtils


class ThingEngine(ThingBaseEngine, SensorThingsUtils):
    def get_things(
        self,
        thing_ids: Optional[list[UUID]] = None,
        location_ids: Optional[list[UUID]] = None,
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

        things = Thing.objects

        if thing_ids:
            things = things.filter(id__in=thing_ids)

        if location_ids:
            things = things.filter(locations__id__in=location_ids)

        things = things.prefetch_related(
            "locations", "thing_file_attachments", "thing_tags"
        ).visible(
            principal=self.request.principal  # noqa
        )

        if filters:
            things = self.apply_filters(
                queryset=things, component=ThingSchema, filters=filters
            )

        if ordering:
            things = self.apply_order(
                queryset=things, component=ThingSchema, order_by=ordering
            )

        things = things.distinct()

        if get_count:
            count = things.count()
        else:
            count = None

        if pagination:
            things = self.apply_pagination(
                queryset=things, top=pagination.get("top"), skip=pagination.get("skip")
            )

        try:
            return {
                thing.id: {
                    "id": thing.id,
                    "name": thing.name,
                    "description": thing.description,
                    "properties": {
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
                            file_attachment.name: file_attachment.link
                            for file_attachment in thing.thing_file_attachments.all()
                        },
                    },
                    "location_ids": [location.id for location in thing.locations.all()],
                }
                for thing in things
            }, count
        except (
            DataError,
            DatabaseError,
        ) as e:
            raise HttpError(400, str(e))

    def create_thing(self, thing) -> str:
        raise HttpError(403, "You do not have permission to perform this action.")

    def update_thing(self, thing_id: str, thing) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")

    def delete_thing(self, thing_id: str) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")
