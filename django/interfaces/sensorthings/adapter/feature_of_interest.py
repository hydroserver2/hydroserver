from django.db.utils import DataError, DatabaseError
from ninja.errors import HttpError
from sensorthings.types import Absent
from sensorthings.versions.v1_1.dto import (
    CollectionDTO,
    EntityResultSetDTO,
    FeatureOfInterestDTO,
)

from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import MonitoringSite, Observation

from .utils import SensorThingsUtils


class FeatureOfInterestMixin(SensorThingsUtils):
    def get_features_of_interest(
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
        principal = context.principal if context else AnonymousPrincipal()
        sites = principal.filter_by_permission(MonitoringSite.objects, "can_view")

        if filters:
            sites = self.apply_filters(
                sites, MonitoringSite, filters, entity_name="FeatureOfInterest"
            )
        if orderby:
            sites = self.apply_order(
                sites, MonitoringSite, orderby, entity_name="FeatureOfInterest"
            )
        sites = sites.distinct()

        if group_by and group_by[0] == "feature_of_interest":
            sites = sites.filter(pk__in=group_by[1])
            site_list = list(sites)
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_ids=[site.id for site in site_list]
                )
            }
        elif group_by and group_by[0] in {"observation", "observations"}:
            observations = principal.filter_by_permission(Observation.objects, "can_view")
            observations = observations.filter(pk__in=group_by[1])
            observation_sites = dict(
                observations.values_list("id", "datastream__monitoring_site_id")
            )
            site_ids = set(observation_sites.values())
            site_list = list(sites.filter(pk__in=site_ids))
            visible_site_ids = {site.id for site in site_list}
            collections = {
                observation_id: CollectionDTO(
                    entity_count=(
                        1
                        if count
                        and observation_sites.get(observation_id) in visible_site_ids
                        else 0 if count else None
                    ),
                    entity_ids=(
                        [observation_sites[observation_id]]
                        if observation_sites.get(observation_id) in visible_site_ids
                        else []
                    ),
                )
                for observation_id in group_by[1]
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
                site.id: FeatureOfInterestDTO(
                    id=self.select_field(select, "id", site.id),
                    name=self.select_field(select, "name", site.name),
                    description=self.select_field(
                        select, "description", site.description
                    ),
                    encoding_type="application/geo+json",
                    feature=(
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
                        if select is None or "feature" in select
                        else Absent
                    ),
                    properties=(
                        {
                            "elevation_m": site.elevation_m,
                            "elevation_datum": site.elevation_datum,
                            "admin_area_1": site.admin_area_1,
                            "admin_area_2": site.admin_area_2,
                            "country": site.country,
                        }
                        if select is None or "properties" in select
                        else Absent
                    ),
                )
                for site in site_list
            }
        except (DataError, DatabaseError) as error:
            raise HttpError(400, str(error))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_features_of_interest(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_features_of_interest(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_features_of_interest(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
