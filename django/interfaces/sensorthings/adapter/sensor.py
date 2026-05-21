from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.types import Absent
from core.sta.models import Sensor
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, SensorDTO
from .utils import SensorThingsUtils


class SensorMixin(SensorThingsUtils):

    def get_sensors(self, filters=None, orderby=None, group_by=None, select=None,
                    top=100, skip=0, count=False, context=None):
        needs_properties = select is None or "properties" in select

        sensors = Sensor.objects
        if needs_properties:
            sensors = sensors.select_related("workspace")
        sensors = sensors.visible(principal=context.principal if context else None)

        if filters:
            sensors = self.apply_filters(sensors, Sensor, filters)
        if orderby:
            sensors = self.apply_order(sensors, Sensor, orderby)
        sensors = sensors.distinct()

        if group_by and group_by[0] == "sensor":
            sensors = sensors.filter(pk__in=group_by[1])
            sensor_list = list(sensors)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[sensor.id for sensor in sensor_list])
            }
        else:
            entity_count = sensors.count() if count else None
            sensor_list = list(self.apply_pagination(sensors, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[sensor.id for sensor in sensor_list],
                )
            }

        try:
            entities = {
                sensor.id: SensorDTO(
                    id=self.select_field(select, "id", sensor.id),
                    name=self.select_field(select, "name", sensor.name),
                    description=self.select_field(select, "description", sensor.description),
                    encoding_type=self.select_field(select, "encoding_type", sensor.encoding_type),
                    metadata=(
                        {
                            "method_code": sensor.method_code,
                            "method_type": sensor.method_type,
                            "method_link": sensor.method_link,
                            "sensor_model": {
                                "sensor_model_name": sensor.sensor_model,
                                "sensor_model_url": sensor.sensor_model_link,
                                "sensor_manufacturer": sensor.manufacturer,
                            },
                        }
                        if select is None or "metadata" in select else Absent
                    ),
                    properties=(
                        {
                            "workspace": (
                                {
                                    "id": sensor.workspace.id,
                                    "name": sensor.workspace.name,
                                    "link": sensor.workspace.link,
                                    "is_private": sensor.workspace.is_private,
                                }
                                if sensor.workspace else None
                            ),
                        }
                        if needs_properties else Absent
                    ),
                )
                for sensor in sensor_list
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
