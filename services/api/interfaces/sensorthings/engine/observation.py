import math
from uuid import UUID
from typing import Optional
from django.db.models.functions import Coalesce
from django.db.models import Min, Max, Count, Q, Value, OuterRef, Subquery
from django.db.utils import IntegrityError, DatabaseError, DataError
from django.contrib.postgres.aggregates import ArrayAgg
from psycopg.errors import UniqueViolation
from ninja.errors import HttpError
from domains.sta.models import Observation, Datastream
from sensorthings.components.observations.engine import ObservationBaseEngine
from sensorthings.components.observations.schemas import (
    Observation as ObservationSchema,
    ObservationPatchBody,
)
from ..schemas import ObservationPostBody
from .utils import SensorThingsUtils
from domains.sta.services.observation import ObservationService
from domains.sta.services.datastream import DatastreamService

observation_service = ObservationService()
datastream_service = DatastreamService()


class ObservationEngine(ObservationBaseEngine, SensorThingsUtils):
    def get_observations(
        self,
        observation_ids: Optional[list[UUID]] = None,
        datastream_ids: Optional[list[UUID]] = None,
        feature_of_interest_ids: Optional[list[UUID]] = None,
        pagination: Optional[dict] = None,
        ordering: Optional[dict] = None,
        filters: Optional[dict] = None,
        expanded: bool = False,
        get_count: bool = False,
    ) -> (list[dict], int):

        if observation_ids:
            observation_ids = self.strings_to_uuids(observation_ids)

        observations = Observation.objects

        if observation_ids:
            observations = observations.filter(id__in=observation_ids)

        observations = observations.visible(principal=self.request.principal)  # noqa

        if filters:
            observations = self.apply_filters(
                queryset=observations, component=ObservationSchema, filters=filters
            )

        if not ordering:
            ordering = []

        if not all(
            field in [order_rule["field"] for order_rule in ordering]
            for field in ["Datastream/id", "phenomenonTime"]
        ):
            timestamp_direction = next(
                iter(
                    [
                        order_rule["direction"]
                        for order_rule in ordering
                        if order_rule["field"] == "phenomenonTime"
                    ]
                ),
                "asc",
            )
            ordering = [
                {"field": "Datastream/id", "direction": "asc"},
                {"field": "phenomenonTime", "direction": timestamp_direction},
            ] + [
                order_rule
                for order_rule in ordering
                if order_rule["field"] not in ["Datastream/id", "phenomenonTime"]
            ]

        result_qualifier_subquery = (
            Observation.result_qualifiers.through.objects.filter(
                **{"observation": OuterRef("pk")}
            )
            .values("observation")
            .annotate(
                codes=ArrayAgg(
                    f"resultqualifier__code",
                    distinct=True,
                    filter=~Q(**{"resultqualifier__code": None}),
                )
            )
            .values("codes")[:1]
        )

        observations = observations.annotate(
            result_qualifier_codes=Coalesce(
                Subquery(result_qualifier_subquery), Value([])
            )
        )

        observations = self.apply_order(
            queryset=observations, component=ObservationSchema, order_by=ordering
        )

        observations = observations.distinct()

        if get_count:
            count = observations.count()
        else:
            count = None

        if datastream_ids:
            observations = self.apply_window(
                queryset=observations,
                partition_field="datastream_id",
                top=pagination.get("top") if pagination else 100,
                skip=pagination.get("skip") if pagination else 0,
            )
        else:
            observations = self.apply_pagination(
                queryset=observations,
                top=pagination.get("top") if pagination else 100,
                skip=pagination.get("skip") if pagination else 0,
            )

        try:
            return {
                observation.id: {
                    "id": observation.id,
                    "phenomenon_time": str(observation.phenomenon_time),
                    "result": observation.result,
                    "result_time": (
                        str(observation.result_time)
                        if observation.result_time
                        else None
                    ),
                    "datastream_id": observation.datastream_id,
                    "result_quality": {
                        "quality_code": observation.quality_code,
                        "result_qualifiers": observation.result_qualifier_codes
                        if observation.result_qualifiers is not None else []
                    }
                }
                for observation in observations
            }, count
        except (
            DatabaseError,
            DataError,
        ) as e:
            raise HttpError(400, str(e))

    def create_observation(self, observation: ObservationPostBody) -> UUID:
        datastream = datastream_service.get_datastream_for_action(
            principal=self.request.principal,  # noqa
            uid=observation.datastream.id,
            action="view",
        )

        if not Observation.can_principal_create(
            principal=self.request.principal,  # noqa
            workspace=datastream.thing.workspace,
        ):
            raise HttpError(
                403, "You do not have permission to create this observation"
            )

        try:
            new_observation = Observation.objects.create(
                datastream_id=observation.datastream.id,
                phenomenon_time=observation.phenomenon_time,
                result=(
                    observation.result
                    if not math.isnan(observation.result)
                    else datastream.no_data_value
                ),
                result_time=observation.result_time,
                quality_code=(
                    observation.result_quality.quality_code
                    if observation.result_quality
                    else None
                ),
                # result_qualifiers=observation.result_quality.result_qualifiers if observation.result_quality else []
            )
        except IntegrityError:
            raise HttpError(409, "Duplicate phenomenonTime found on this datastream.")

        self.update_value_count(datastream_id=observation.datastream.id)

        return new_observation.id

    def create_observations(self, observations) -> list[UUID]:

        new_observations = []

        for datastream_id, datastream_observations in observations.items():
            datastream = datastream_service.get_datastream_for_action(
                principal=self.request.principal,  # noqa
                uid=datastream_id,
                action="view",
            )

            if not Observation.can_principal_create(
                principal=self.request.principal,  # noqa
                workspace=datastream.thing.workspace,
            ):
                raise HttpError(
                    403, "You do not have permission to create these observations"
                )

            # for result_qualifier_id in list(set([result_qualifier for result_qualifiers in [
            #     observation.result_quality.result_qualifiers
            #     for observation in datastream_observations
            #     if observation.result_quality and observation.result_quality.result_qualifiers
            # ] for result_qualifier in result_qualifiers])):
            #     ResultQualifier.objects.get_by_id(
            #         result_qualifier_id=result_qualifier_id,
            #         principal=getattr(self, "http").principal,
            #         method="GET",
            #         fetch=False,
            #         raise_404=True
            #     )

            try:
                new_observations_for_datastream = Observation.objects.bulk_copy(
                    [
                        Observation(
                            datastream_id=observation.datastream.id,
                            phenomenon_time=observation.phenomenon_time,
                            result=(
                                observation.result
                                if not math.isnan(observation.result)
                                else datastream.no_data_value
                            ),
                            result_time=observation.result_time,
                            quality_code=(
                                observation.result_quality.quality_code
                                if observation.result_quality
                                else None
                            ),
                            # result_qualifiers=observation.result_quality.result_qualifiers
                            # if observation.result_quality else []
                        )
                        for observation in datastream_observations
                    ]
                )
            except (
                IntegrityError,
                UniqueViolation,
            ):
                raise HttpError(
                    409, "Duplicate phenomenonTime found on this datastream."
                )

            new_observations.extend(new_observations_for_datastream)

            self.update_value_count(datastream_id=datastream_id)

        return [observation.id for observation in new_observations]

    def update_observation(
        self, observation_id: str, observation: ObservationPatchBody
    ) -> None:
        pass

    def delete_observation(self, observation_id: str) -> None:
        pass

    @staticmethod
    def update_value_count(datastream_id: UUID) -> None:

        aggregate = Observation.objects.filter(datastream_id=datastream_id).aggregate(
            min_time=Min("phenomenon_time"),
            max_time=Max("phenomenon_time"),
            count=Count("id"),
        )

        datastream = Datastream.objects.get(pk=datastream_id)

        datastream.phenomenon_begin_time = aggregate["min_time"]
        datastream.phenomenon_end_time = aggregate["max_time"]
        datastream.value_count = aggregate["count"]

        datastream.save()
