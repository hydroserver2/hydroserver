from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from django.db.models import Count
from sensorthings.types import Absent
from core.sta.models import Datastream
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, DatastreamDTO
from core.sta.services.datastream import DatastreamService
from .utils import SensorThingsUtils

datastream_service = DatastreamService()

_GROUP_BY_PARTITION = {
    "thing": "thing_id",
    "sensor": "sensor_id",
    "observed_property": "observed_property_id",
}


class DatastreamMixin(SensorThingsUtils):

    def get_datastreams(self, filters=None, orderby=None, group_by=None, select=None,
                        top=100, skip=0, count=False, context=None):
        needs_unit = select is None or "unit_of_measurement" in select
        needs_properties = select is None or "properties" in select

        datastreams = Datastream.objects
        related = []
        if needs_unit or needs_properties:
            related.append("unit")
        if needs_properties:
            related += ["processing_level", "thing__workspace"]
        if related:
            datastreams = datastreams.select_related(*related)
        if needs_properties:
            datastreams = datastreams.prefetch_related(
                "datastream_file_attachments", "datastream_tags"
            )
        datastreams = datastreams.visible(principal=context.principal if context else None)

        if filters:
            datastreams = self.apply_filters(datastreams, Datastream, filters)
        if orderby:
            datastreams = self.apply_order(datastreams, Datastream, orderby)
        datastreams = datastreams.distinct()

        if group_by and group_by[0] == "datastream":
            datastreams = datastreams.filter(pk__in=group_by[1])
            ds_list = list(datastreams)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[datastream.id for datastream in ds_list])
            }
        elif group_by and (partition_field := _GROUP_BY_PARTITION.get(group_by[0])):
            datastreams = datastreams.filter(**{f"{group_by[0]}_id__in": group_by[1]})
            ds_counts = dict(
                datastreams
                .values(group_by[0])
                .annotate(total=Count("id"))
                .values_list(group_by[0], "total")
            ) if count else None
            ds_list = list(self.apply_window(datastreams, partition_field, top, skip))
            groups = {}
            for datastream in ds_list:
                groups.setdefault(getattr(datastream, partition_field), []).append(datastream.id)
            collections = {
                pid: CollectionDTO(
                    entity_count=int(ds_counts.get(pid, 0)) if count else None,
                    entity_ids=groups.get(pid, [])
                ) for pid in group_by[1]
            }
        else:
            entity_count = datastreams.count() if count else None
            ds_list = list(self.apply_pagination(datastreams, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[ds.id for ds in ds_list],
                )
            }

        try:
            entities = {
                datastream.id: DatastreamDTO(
                    id=self.select_field(select, "id", datastream.id),
                    name=self.select_field(select, "name", str(datastream.name)),
                    description=self.select_field(select, "description", datastream.description),
                    observation_type="http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                    observed_area=self.select_field(select, "observed_area", datastream.observed_area),
                    phenomenon_time=self.select_field(
                        select, "phenomenon_time",
                        self.iso_time_interval(datastream.phenomenon_begin_time, datastream.phenomenon_end_time),
                    ),
                    result_time=self.select_field(
                        select, "result_time",
                        self.iso_time_interval(datastream.result_begin_time, datastream.result_end_time),
                    ),
                    unit_of_measurement=(
                        {
                            "name": datastream.unit.name,
                            "symbol": datastream.unit.symbol,
                            "definition": datastream.unit.definition.split(";")[0],
                        }
                        if needs_unit else Absent
                    ),
                    properties=(
                        {
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
                                fa.name: fa.link
                                for fa in datastream.datastream_file_attachments.all()
                            },
                        }
                        if needs_properties else Absent
                    ),
                    thing_id=datastream.thing_id,
                    sensor_id=datastream.sensor_id,
                    observed_property_id=datastream.observed_property_id,
                )
                for datastream in ds_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_datastreams(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_datastreams(self, payload, context=None):
        for datastream_id, dto in payload.items():
            datastream = datastream_service.get_datastream_for_action(
                principal=context.principal if context else None,
                uid=datastream_id,
                action="edit",
            )

            if dto.phenomenon_time is not None:
                parts = str(dto.phenomenon_time).split("/")
                datastream.phenomenon_begin_time = parts[0]
                datastream.phenomenon_end_time = parts[-1]
            else:
                datastream.phenomenon_begin_time = None
                datastream.phenomenon_end_time = None

            if dto.result_time is not None:
                parts = str(dto.result_time).split("/")
                datastream.result_begin_time = parts[0]
                datastream.result_end_time = parts[-1]
            else:
                datastream.result_begin_time = None
                datastream.result_end_time = None

            datastream.save()

    def delete_datastreams(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
