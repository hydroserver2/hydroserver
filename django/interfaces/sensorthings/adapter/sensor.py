from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.types import Absent
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Method
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, SensorDTO
from .utils import SensorThingsUtils


class SensorMixin(SensorThingsUtils):

    def get_sensors(self, filters=None, orderby=None, group_by=None, select=None,
                    top=100, skip=0, count=False, context=None):
        needs_properties = select is None or "properties" in select
        principal = context.principal if context else AnonymousPrincipal()

        methods = Method.objects
        if needs_properties:
            methods = methods.select_related("workspace")
        methods = principal.filter_by_permission(methods, "can_view")

        if filters:
            methods = self.apply_filters(methods, Method, filters, entity_name="Sensor")
        if orderby:
            methods = self.apply_order(methods, Method, orderby, entity_name="Sensor")
        methods = methods.distinct()

        if group_by and group_by[0] == "sensor":
            methods = methods.filter(pk__in=group_by[1])
            method_list = list(methods)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[method.id for method in method_list])
            }
        else:
            entity_count = methods.count() if count else None
            method_list = list(self.apply_pagination(methods, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[method.id for method in method_list],
                )
            }

        try:
            entities = {
                method.id: SensorDTO(
                    id=self.select_field(select, "id", method.id),
                    name=self.select_field(select, "name", method.name),
                    description=self.select_field(select, "description", method.description),
                    encoding_type=self.select_field(
                        select, "encoding_type", "application/json"
                    ),
                    metadata=(
                        {
                            "method_code": method.code,
                            "method_type": method.type,
                            "method_link": method.definition,
                            "sensor_model": {
                                "sensor_model_name": method.sensor_model,
                                "sensor_model_url": method.sensor_model_definition,
                                "sensor_manufacturer": method.sensor_model_manufacturer,
                            },
                        }
                        if select is None or "metadata" in select else Absent
                    ),
                    properties=(
                        {
                            "workspace": (
                                {
                                    "id": method.workspace.id,
                                    "name": method.workspace.name,
                                    "is_private": method.workspace.is_private,
                                }
                                if method.workspace else None
                            ),
                        }
                        if needs_properties else Absent
                    ),
                )
                for method in method_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_sensors(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_sensors(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_sensors(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
