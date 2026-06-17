import math
from ninja.errors import HttpError
from django.db.models import Min, Max, Count, F, Sum
from django.db.utils import IntegrityError, DatabaseError, DataError
from psycopg.errors import UniqueViolation
from sensorthings.types import Absent
from core.sta.models import Observation, Datastream
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO, ObservationDTO
from core.sta.services.datastream import DatastreamService
from .utils import SensorThingsUtils

datastream_service = DatastreamService()


class ObservationMixin(SensorThingsUtils):

    def get_observations(self, filters=None, orderby=None, group_by=None, select=None,
                         top=100, skip=0, count=False, context=None):
        needs_result_quality = select is None or "result_quality" in select

        observations = Observation.objects.visible(
            principal=context.principal if context else None
        )

        if filters:
            observations = self.apply_filters(observations, Observation, filters)

        if not orderby or not all(
            field in ["/".join(f.path) for f in orderby]
            for field in ["Datastream/id", "phenomenonTime"]
        ):
            observations = observations.order_by("datastream_id", "phenomenon_time")
        else:
            observations = self.apply_order(observations, Observation, orderby)

        if needs_result_quality:
            observations = observations.annotate(
                result_qualifier_codes=F("result_qualifiers")
            )

        observations = observations.distinct()

        if group_by and group_by[0] == "observation":
            observations = observations.filter(pk__in=group_by[1])
            obs_list = list(observations)
            collections = {
                "__UNGROUPED__": CollectionDTO(entity_ids=[o.id for o in obs_list])
            }
        elif group_by and group_by[0] == "datastream":
            observations = observations.filter(datastream_id__in=group_by[1])
            obs_counts = dict(
                observations
                .values(group_by[0])
                .annotate(total=Count("id"))
                .values_list(group_by[0], "total")
            ) if count else None
            obs_list = list(self.apply_window(observations, "datastream_id", top, skip))
            groups = {}
            for obs in obs_list:
                groups.setdefault(obs.datastream_id, []).append(obs.id)
            collections = {
                pid: CollectionDTO(
                    entity_count=int(obs_counts.get(pid, 0)) if count else None,
                    entity_ids=groups.get(pid, [])
                ) for pid in group_by[1]
            }
        else:
            if count and not filters:
                entity_count = Datastream.objects.visible(
                    principal=context.principal if context else None
                ).aggregate(total=Sum("value_count"))["total"] or 0
            elif count:
                entity_count = observations.count() if count else None
            else:
                entity_count = None

            obs_list = list(self.apply_pagination(observations, top, skip))
            collections = {
                "__UNGROUPED__": CollectionDTO(
                    entity_count=entity_count,
                    entity_ids=[o.id for o in obs_list],
                )
            }

        try:
            entities = {
                obs.id: ObservationDTO(
                    id=self.select_field(select, "id", obs.id),
                    phenomenon_time=self.select_field(
                        select, "phenomenon_time", str(obs.phenomenon_time)
                    ),
                    result=self.select_field(select, "result", obs.result),
                    result_time=self.select_field(
                        select, "result_time",
                        str(obs.result_time) if obs.result_time else None,
                    ),
                    result_quality=(
                        {
                            "quality_code": obs.quality_code,
                            "result_qualifiers": obs.result_qualifier_codes,
                        }
                        if needs_result_quality else Absent
                    ),
                    datastream_id=obs.datastream_id,
                )
                for obs in obs_list
            }
        except (DataError, DatabaseError) as e:
            raise HttpError(400, str(e))

        return EntityResultSetDTO(collections=collections, entities=entities)

    def create_observations(self, payload, context=None):
        principal = context.principal if context else None

        by_datastream = {}
        for dto in payload:
            by_datastream.setdefault(dto.datastream_id, []).append(dto)

        new_ids = []

        for datastream_id, dtos in by_datastream.items():
            datastream = datastream_service.get_datastream_for_action(
                principal=principal,
                uid=datastream_id,
                action="view",
            )

            if not Observation.can_principal_create(
                principal=principal,
                workspace=datastream.thing.workspace,
            ):
                raise HttpError(
                    403, "You do not have permission to create observations on this datastream."
                )

            try:
                new_observations = Observation.objects.bulk_copy([
                    Observation(
                        datastream_id=datastream_id,
                        phenomenon_time=dto.phenomenon_time,
                        result=(
                            dto.result
                            if not (isinstance(dto.result, float) and math.isnan(dto.result))
                            else datastream.no_data_value
                        ),
                        result_time=dto.result_time if dto.result_time is not None else None,
                        quality_code=(
                            dto.result_quality.get("quality_code")
                            if dto.result_quality
                            else None
                        ),
                    )
                    for dto in dtos
                ])
            except (IntegrityError, UniqueViolation):
                raise HttpError(409, "Duplicate phenomenonTime found on this datastream.")

            new_ids.extend(obs.id for obs in new_observations)
            self._update_value_count(datastream_id)

        return new_ids

    def update_observations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_observations(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")

    @staticmethod
    def _update_value_count(datastream_id):
        aggregate = Observation.objects.filter(datastream_id=datastream_id).aggregate(
            min_time=Min("phenomenon_time"),
            max_time=Max("phenomenon_time"),
            count=Count("id"),
        )
        Datastream.objects.filter(pk=datastream_id).update(
            phenomenon_begin_time=aggregate["min_time"],
            phenomenon_end_time=aggregate["max_time"],
            value_count=aggregate["count"],
        )
