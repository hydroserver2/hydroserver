from uuid import UUID
from typing import Optional
from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from domains.sta.models import Datastream
from sensorthings.components.datastreams.engine import DatastreamBaseEngine
from sensorthings.components.datastreams.schemas import (
    Datastream as DatastreamSchema,
    DatastreamPostBody,
    DatastreamPatchBody,
)
from .utils import SensorThingsUtils
from domains.sta.services.datastream import DatastreamService


datastream_service = DatastreamService()


class DatastreamEngine(DatastreamBaseEngine, SensorThingsUtils):
    def get_datastreams(
        self,
        datastream_ids: Optional[list[UUID]] = None,
        observed_property_ids: Optional[list[UUID]] = None,
        sensor_ids: Optional[list[UUID]] = None,
        thing_ids: Optional[list[UUID]] = None,
        pagination: Optional[dict] = None,
        ordering: Optional[dict] = None,
        filters: Optional[dict] = None,
        expanded: bool = False,
        get_count: bool = False,
    ) -> (list[dict], int):

        if datastream_ids:
            datastream_ids = self.strings_to_uuids(datastream_ids)

        datastreams = Datastream.objects

        if datastream_ids:
            datastreams = datastreams.filter(id__in=datastream_ids)

        datastreams = datastreams.select_related(
            "processing_level", "unit", "thing__workspace"
        ).prefetch_related(
            "datastream_file_attachments", "datastream_tags"
        ).visible(
            principal=self.request.principal  # noqa
        )

        if filters:
            datastreams = self.apply_filters(
                queryset=datastreams, component=DatastreamSchema, filters=filters
            )

        if ordering:
            datastreams = self.apply_order(
                queryset=datastreams, component=DatastreamSchema, order_by=ordering
            )

        datastreams = datastreams.distinct()

        if get_count:
            count = datastreams.count()
        else:
            count = None

        if thing_ids:
            datastreams = self.apply_window(
                queryset=datastreams,
                partition_field="thing_id",
            )
        elif sensor_ids:
            datastreams = self.apply_window(
                queryset=datastreams,
                partition_field="sensor_id",
            )
        elif observed_property_ids:
            datastreams = self.apply_window(
                queryset=datastreams,
                partition_field="observed_property_id",
            )
        else:
            if pagination:
                datastreams = self.apply_pagination(
                    queryset=datastreams,
                    top=pagination.get("top"),
                    skip=pagination.get("skip"),
                )
            datastreams = datastreams.all()

        try:
            return {
                datastream.id: {
                    "id": datastream.id,
                    "name": str(datastream.name),
                    "description": datastream.description,
                    "thing_id": datastream.thing_id,
                    "sensor_id": datastream.sensor_id,
                    "observed_property_id": datastream.observed_property_id,
                    "unit_of_measurement": {
                        "name": datastream.unit.name,
                        "symbol": datastream.unit.symbol,
                        "definition": datastream.unit.definition.split(";")[0],
                    },
                    "observation_type": datastream.observation_type,
                    "phenomenon_time": getattr(self, "iso_time_interval")(
                        datastream.phenomenon_begin_time, datastream.phenomenon_end_time
                    ),
                    "result_time": getattr(self, "iso_time_interval")(
                        datastream.result_begin_time, datastream.result_end_time
                    ),
                    "properties": {
                        "result_type": datastream.result_type,
                        "status": datastream.status,
                        "sampled_medium": datastream.sampled_medium,
                        "value_count": datastream.value_count,
                        "no_data_value": datastream.no_data_value,
                        "processing_level_code": datastream.processing_level.code,
                        "processing_level_id": datastream.processing_level.id,
                        "unit_id": datastream.unit.id,
                        "intended_time_spacing": datastream.intended_time_spacing,
                        "intended_time_spacing_unit_of_measurement": datastream.intended_time_spacing_unit,
                        "aggregation_statistic": datastream.aggregation_statistic,
                        "time_aggregation_interval": datastream.time_aggregation_interval,
                        "time_aggregation_interval_unit_of_measurement": datastream.time_aggregation_interval_unit,
                        "is_private": datastream.is_private,
                        "is_visible": datastream.is_visible,
                        "workspace": {
                            "id": datastream.thing.workspace.id,
                            "name": datastream.thing.workspace.name,
                            "link": datastream.thing.workspace.link,
                            "is_private": datastream.thing.workspace.is_private,
                        },
                        "tags": {tag.key: tag.value for tag in datastream.datastream_tags.all()},
                        "file_attachments": {
                            file_attachment.name: file_attachment.link
                            for file_attachment in datastream.datastream_file_attachments.all()
                        },
                    },
                }
                for datastream in datastreams
            }, count
        except (
            DatabaseError,
            DataError,
        ) as e:
            raise HttpError(400, str(e))

    def create_datastream(self, datastream: DatastreamPostBody) -> UUID:
        raise HttpError(403, "You do not have permission to perform this action.")

    def update_datastream(
        self, datastream_id: UUID, datastream: DatastreamPatchBody
    ) -> None:

        datastream_obj = datastream_service.get_datastream_for_action(
            principal=self.request.principal,  # noqa
            uid=datastream_id,
            action="edit",
        )

        datastream_data = datastream.dict(exclude_unset=True)

        if datastream_data.get("phenomenon_time", None) is not None:
            datastream_obj.phenomenon_begin_time = datastream_data[
                "phenomenon_time"
            ].split("/")[0]
            datastream_obj.phenomenon_end_time = datastream_data[
                "phenomenon_time"
            ].split("/")[-1]
        else:
            datastream_obj.phenomenon_begin_time = None
            datastream_obj.phenomenon_end_time = None

        if datastream_data.get("result_time", None) is not None:
            datastream_obj.result_begin_time = datastream_data["result_time"].split(
                "/"
            )[0]
            datastream_obj.result_end_time = datastream_data["result_time"].split("/")[
                -1
            ]
        else:
            datastream_obj.result_begin_time = None
            datastream_obj.result_end_time = None

        datastream_obj.save()

    def delete_datastream(self, datastream_id: UUID) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")
