from django.db.utils import DataError, DatabaseError
from ninja.errors import HttpError
from sensorthings.types import Absent
from sensorthings.versions.v1_1.dto import CollectionDTO, EntityResultSetDTO, LocationDTO

from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import MonitoringSite

from .utils import SensorThingsUtils


class LocationMixin(SensorThingsUtils):
    def get_locations(
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

        sites = principal.filter_by_permission(MonitoringSite.objects, "can_view")
        if needs_properties:
            sites = sites.select_related("workspace")

        if filters:
            sites = self.apply_filters(
                sites, MonitoringSite, filters, entity_name="Location"
            )
        if orderby:
            sites = self.apply_order(
                sites, MonitoringSite, orderby, entity_name="Location"
            )
        sites = sites.distinct()

        if group_by and group_by[0] == "location":
            sites = sites.filter(pk__in=group_by[1])
            site_list = list(sites)
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_ids=[site.id for site in site_list]
                )
            }
        elif group_by and group_by[0] in {"thing", "things"}:
            sites = sites.filter(pk__in=group_by[1])
            site_list = list(sites)
            site_ids = {site.id for site in site_list}
            collections = {
                thing_id: CollectionDTO(
                    entity_count=(1 if thing_id in site_ids else 0) if count else None,
                    entity_ids=[thing_id] if thing_id in site_ids else [],
                )
                for thing_id in group_by[1]
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
                site.id: LocationDTO(
                    id=self.select_field(select, "id", site.id),
                    name=self.select_field(select, "name", site.name),
                    description=self.select_field(
                        select, "description", site.description
                    ),
                    encoding_type="application/geo+json",
                    location=(
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    float(site.longitude),
                                    float(site.latitude),
                                ],
                            },
                        }
                        if select is None or "location" in select
                        else Absent
                    ),
                    properties=(
                        {
                            "elevation_m": site.elevation_m,
                            "elevation_datum": site.elevation_datum,
                            "admin_area_1": site.admin_area_1,
                            "admin_area_2": site.admin_area_2,
                            "country": site.country,
                            "workspace": {
                                "id": site.workspace.id,
                                "name": site.workspace.name,
                                "is_private": site.workspace.is_private,
                            },
                        }
                        if needs_properties
                        else Absent
                    ),
                    thing_ids=[site.id],
                )
                for site in site_list
            }
        except (DataError, DatabaseError) as error:
            raise HttpError(400, str(error))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_locations(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
