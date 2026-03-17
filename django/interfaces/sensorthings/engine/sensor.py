from typing import Optional
from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from sensorthings.components.sensors.engine import SensorBaseEngine
from sensorthings.components.sensors.schemas import Sensor as SensorSchema
from domains.sta.models import Sensor
from .utils import SensorThingsUtils


class SensorEngine(SensorBaseEngine, SensorThingsUtils):
    def get_sensors(
        self,
        sensor_ids: Optional[list[str]] = None,
        pagination: Optional[dict] = None,
        ordering: Optional[dict] = None,
        filters: Optional[dict] = None,
        expanded: bool = False,
        get_count: bool = False,
    ) -> (list[dict], int):

        if sensor_ids:
            sensor_ids = self.strings_to_uuids(sensor_ids)

        sensors = Sensor.objects

        if sensor_ids:
            sensors = sensors.filter(id__in=sensor_ids)

        sensors = sensors.visible(principal=self.request.principal)  # noqa

        if filters:
            sensors = self.apply_filters(
                queryset=sensors, component=SensorSchema, filters=filters
            )

        if ordering:
            sensors = self.apply_order(
                queryset=sensors, component=SensorSchema, order_by=ordering
            )

        sensors = sensors.distinct()

        if get_count:
            count = sensors.count()
        else:
            count = None

        if pagination:
            sensors = self.apply_pagination(
                queryset=sensors, top=pagination.get("top"), skip=pagination.get("skip")
            )

        try:
            return {
                sensor.id: {
                    "id": sensor.id,
                    "name": sensor.name,
                    "description": sensor.description,
                    "encoding_type": sensor.encoding_type,
                    "sensor_metadata": {
                        "method_code": sensor.method_code,
                        "method_type": sensor.method_type,
                        "method_link": sensor.method_link,
                        "sensor_model": {
                            "sensor_model_name": sensor.sensor_model,
                            "sensor_model_url": sensor.sensor_model_link,
                            "sensor_manufacturer": sensor.manufacturer,
                        },
                    },
                    "properties": {
                        "workspace": (
                            {
                                "id": sensor.workspace.id,
                                "name": sensor.workspace.name,
                                "link": sensor.workspace.link,
                                "is_private": sensor.workspace.is_private,
                            }
                            if sensor.workspace
                            else None
                        ),
                    },
                }
                for sensor in sensors
            }, count
        except (
            DataError,
            DatabaseError,
        ) as e:
            raise HttpError(400, str(e))

    def create_sensor(self, sensor) -> str:
        raise HttpError(403, "You do not have permission to perform this action.")

    def update_sensor(self, sensor_id: str, sensor) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")

    def delete_sensor(self, sensor_id: str) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")
