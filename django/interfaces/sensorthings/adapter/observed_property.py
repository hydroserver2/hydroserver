from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.types import Absent
from core.sta.models import ObservedProperty
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, ObservedPropertyDTO
from .utils import SensorThingsUtils


class ObservedPropertyMixin(SensorThingsUtils):

    def get_observed_properties(self, filters=None, orderby=None, group_by=None,
                                select=None, top=100, skip=0, count=False, context=None):
        needs_properties = select is None or "properties" in select

        observed_properties = ObservedProperty.objects
        if needs_properties:
            observed_properties = observed_properties.select_related("workspace")
        observed_properties = observed_properties.visible(
            principal=context.principal if context else None
        )

        if filters:
            observed_properties = self.apply_filters(
                observed_properties, ObservedProperty, filters
            )
        if orderby:
            observed_properties = self.apply_order(
                observed_properties, ObservedProperty, orderby
            )
        observed_properties = observed_properties.distinct()

        if group_by and group_by[0] == "observed_property":
            observed_properties = observed_properties.filter(pk__in=group_by[1])
            op_list = list(observed_properties)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[observed_property.id for observed_property in op_list])
            }
        else:
            entity_count = observed_properties.count() if count else None
            op_list = list(self.apply_pagination(observed_properties, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[observed_property.id for observed_property in op_list],
                )
            }

        try:
            entities = {
                observed_property.id: ObservedPropertyDTO(
                    id=self.select_field(select, "id", observed_property.id),
                    name=self.select_field(select, "name", observed_property.name),
                    description=self.select_field(select, "description", observed_property.description),
                    definition=self.select_field(select, "definition", observed_property.definition),
                    properties=(
                        {
                            "variable_code": observed_property.code,
                            "variable_type": observed_property.observed_property_type,
                            "workspace": (
                                {
                                    "id": observed_property.workspace.id,
                                    "name": observed_property.workspace.name,
                                    "link": observed_property.workspace.link,
                                    "is_private": observed_property.workspace.is_private,
                                }
                                if observed_property.workspace else None
                            ),
                        }
                        if needs_properties else Absent
                    ),
                )
                for observed_property in op_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_observed_properties(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_observed_properties(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_observed_properties(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
