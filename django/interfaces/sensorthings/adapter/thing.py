from django.db.utils import DataError, DatabaseError
from ninja.errors import HttpError
from sensorthings.types import Absent
from sensorthings.versions.v1_1.dto import CollectionDTO, EntityResultSetDTO, ThingDTO

from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import MonitoringSite

from .utils import SensorThingsUtils


class ThingMixin(SensorThingsUtils):
    def get_things(
        self,
        filters=None,
        orderby=None,
        group_by=None,
        select=None,
        top=100,
        skip=0,
        count=False,
        context=None,
    ):
        needs_properties = select is None or "properties" in select
        principal = context.principal if context else AnonymousPrincipal()

        sites = MonitoringSite.objects
        if needs_properties:
            sites = sites.select_related("workspace").prefetch_related(
                "monitoring_site_file_attachments", "monitoring_site_tags"
            )
        sites = principal.filter_by_permission(sites, "can_view")

        if filters:
            sites = self.apply_filters(
                sites, MonitoringSite, filters, entity_name="Thing"
            )
        if orderby:
            sites = self.apply_order(
                sites, MonitoringSite, orderby, entity_name="Thing"
            )
        sites = sites.distinct()

        if group_by and group_by[0] == "thing":
            sites = sites.filter(pk__in=group_by[1])
            site_list = list(sites)
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_ids=[site.id for site in site_list]
                )
            }
        elif group_by and group_by[0] in {"location", "locations"}:
            sites = sites.filter(pk__in=group_by[1])
            site_list = list(sites)
            site_ids = {site.id for site in site_list}
            collections = {
                location_id: CollectionDTO(
                    entity_count=(1 if location_id in site_ids else 0)
                    if count
                    else None,
                    entity_ids=[location_id] if location_id in site_ids else [],
                )
                for location_id in group_by[1]
            }
        else:
            entity_count = sites.count() if count else None
            site_list = list(self.apply_pagination(sites, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[site.id for site in site_list],
                )
            }

        try:
            entities = {
                site.id: ThingDTO(
                    id=self.select_field(select, "id", site.id),
                    name=self.select_field(select, "name", site.name),
                    description=self.select_field(
                        select, "description", site.description
                    ),
                    properties=(
                        {
                            "code": site.code,
                            "type": site.type,
                            "data_disclaimer": site.data_disclaimer,
                            "is_private": site.is_private,
                            "workspace": {
                                "id": site.workspace.id,
                                "name": site.workspace.name,
                                "is_private": site.workspace.is_private,
                            },
                            "tags": {
                                tag.key: tag.value
                                for tag in site.monitoring_site_tags.all()
                            },
                            "file_attachments": {
                                attachment.name: attachment.link
                                for attachment in site.monitoring_site_file_attachments.all()
                            },
                        }
                        if needs_properties
                        else Absent
                    ),
                    location_ids=[site.id],
                )
                for site in site_list
            }
        except (DataError, DatabaseError) as error:
            raise HttpError(400, str(error))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_things(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_things(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_things(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
