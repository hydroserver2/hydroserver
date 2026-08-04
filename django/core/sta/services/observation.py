import uuid
import math
import hashlib
from typing import Optional, Literal, get_args
from datetime import datetime
from ninja.errors import HttpError
from pydantic.alias_generators import to_camel
from psycopg.errors import UniqueViolation
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Q, Count, Max, Func, F
from django.db.utils import IntegrityError
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Datastream, Observation, ResultQualifier
from interfaces.api.schemas.sta.observation import (
    ObservationFields,
    ObservationOrderByFields,
    ObservationSummaryResponse,
    ObservationDetailResponse,
    ObservationPostBody,
    ObservationBulkPostBody,
    ObservationBulkColumnarPostBody,
    ObservationBulkDeleteBody,
)
from core.sta.services.datastream import DatastreamService
from core.service import ServiceUtils

User = get_user_model()
datastream_service = DatastreamService()


class ObservationService(ServiceUtils):
    @staticmethod
    def handle_http_404_error(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except HttpError as e:
            if e.status_code == 404:
                raise HttpError(400, str(e))
            else:
                raise e

    def get_observation_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        datastream_id: Optional[uuid.UUID] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Observation.objects.annotate(
            result_qualifier_codes=F("result_qualifiers")
        )
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.select_related("datastream__thing")
        if datastream_id:
            queryset = queryset.filter(id=uid, datastream__id=datastream_id)
        else:
            queryset = queryset.filter(id=uid)
        queryset = principal.annotate_permissions(queryset)

        try:
            observation = queryset.get()
        except Observation.DoesNotExist:
            raise HttpError(404, "Observation does not exist")

        if not principal.can_view(observation):
            raise HttpError(404, "Observation does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(observation):
            raise HttpError(
                403, f"You do not have permission to {action} this observation"
            )

        return observation

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related(
            "datastream", "datastream__thing", "datastream__thing__workspace"
        )

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        datastream_id: Optional[uuid.UUID] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        response_format: Optional[str] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Observation.objects

        if datastream_id:
            datastream = datastream_service.get_datastream_for_action(
                principal, datastream_id, action="view"
            )
            queryset = queryset.filter(datastream=datastream)

        for field in ["phenomenon_time__lte", "phenomenon_time__gte"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if filtering.get("result_qualifier_codes"):
            code_filter = Q()
            for code in filtering["result_qualifier_codes"]:
                code_filter |= Q(result_qualifiers__contains=[code])
            queryset = queryset.filter(code_filter)

        queryset = principal.filter_by_permission(queryset, "can_view")

        # TODO: Can't really fix this until PostgreSQL 18 UUID v7 support
        checksum_result = queryset.aggregate(
            max_id=Max(
                Func(
                    F("id"),
                    function="CAST",
                    template="%(function)s(%(expressions)s AS text)",
                )
            )
        )
        checksum_uuid = (
            uuid.UUID(checksum_result["max_id"]) if checksum_result["max_id"] else None
        )

        queryset = queryset.annotate(
            result_qualifier_codes=F("result_qualifiers")
        )

        if not order_by:
            order_by.append("phenomenonTime")

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(ObservationOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.select_related("datastream__thing")

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        response["X-Checksum"] = self.generate_checksum(checksum_uuid, count)

        if response_format == "row":
            fields = ["phenomenon_time", "result", "result_qualifier_codes"]
            return {
                "fields": [to_camel(field) for field in fields],
                "data": list(queryset.values_list(*fields)),
            }
        elif response_format == "column":
            fields = ["phenomenon_time", "result", "result_qualifier_codes"]
            observations = list(queryset.values_list(*fields))
            return (
                dict(zip(fields, zip(*observations)))
                if observations
                else {to_camel(field): [] for field in fields}
            )
        else:
            return [
                (
                    ObservationDetailResponse.model_validate(observation)
                    if expand_related
                    else ObservationSummaryResponse.model_validate(observation)
                )
                for observation in queryset.all()
            ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        datastream_id: Optional[uuid.UUID] = None,
        expand_related: Optional[bool] = None,
    ):
        observation = self.get_observation_for_action(
            principal=principal,
            uid=uid,
            action="view",
            datastream_id=datastream_id,
            expand_related=expand_related,
        )

        return (
            ObservationDetailResponse.model_validate(observation)
            if expand_related
            else ObservationSummaryResponse.model_validate(observation)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservationPostBody,
        datastream_id: uuid.UUID,
        expand_related: Optional[bool] = None,
        update_datastream_statistics: bool = True,
    ):
        datastream = datastream_service.get_datastream_for_action(
            principal, datastream_id, action="view"
        )
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=datastream.thing.workspace_id
        )

        if not principal.can_create("Observation", workspace=workspace):
            raise HttpError(
                403, "You do not have permission to create this observation"
            )

        try:
            observation = Observation.objects.create(
                pk=data.id,
                datastream=datastream,
                **data.dict(include=set(ObservationFields.model_fields.keys()), exclude=["result_qualifier_codes"]),
            )
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise HttpError(409, "Duplicate phenomenonTime or ID found on this datastream.")

        if data.result_qualifier_codes:
            valid_codes = set(
                principal.filter_by_permission(
                    ResultQualifier.objects.filter(
                        Q(workspace_id=datastream.thing.workspace_id)
                        | Q(workspace__isnull=True)
                    ).filter(code__in=data.result_qualifier_codes),
                    "can_view",
                ).values_list("code", flat=True)
            )
            invalid_codes = set(data.result_qualifier_codes) - valid_codes
            if invalid_codes:
                raise HttpError(
                    400,
                    f"Invalid result qualifier codes: {', '.join(sorted(invalid_codes))}",
                )
            observation.result_qualifiers = data.result_qualifier_codes
            observation.save(update_fields=["result_qualifiers"])

        if update_datastream_statistics is True:
            datastream_service.update_observation_statistics(
                datastream=datastream,
                fields=["phenomenon_begin_time", "phenomenon_end_time", "value_count"],
            )

        return self.get(
            principal=principal,
            uid=observation.id,
            datastream_id=datastream_id,
            expand_related=expand_related,
        )

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        datastream_id: Optional[uuid.UUID] = None,
        update_datastream_statistics: bool = True,
    ):
        datastream = datastream_service.get_datastream_for_action(
            principal, datastream_id, action="view"
        )
        observation = self.get_observation_for_action(
            principal=principal,
            uid=uid,
            action="delete",
            datastream_id=datastream_id,
        )
        observation.delete()

        if update_datastream_statistics is True:
            datastream_service.update_observation_statistics(
                datastream=datastream,
                fields=["phenomenon_begin_time", "phenomenon_end_time", "value_count"],
            )

    def bulk_create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservationBulkPostBody | ObservationBulkColumnarPostBody,
        datastream_id: uuid.UUID,
        mode: Literal["insert", "append", "backfill", "replace"],
        update_datastream_statistics: bool = True,
    ):
        datastream = datastream_service.get_datastream_for_action(
            principal, datastream_id, action="view"
        )
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=datastream.thing.workspace_id
        )

        if not principal.can_create("Observation", workspace=workspace):
            raise HttpError(
                403, "You do not have permission to create these observations"
            )

        required_fields = {"phenomenonTime", "result"}
        if not required_fields.issubset(set(data.fields)):
            raise HttpError(400, "Missing required observation fields")

        field_map = {field: idx for idx, field in enumerate(data.fields)}
        idx_phenomenon = field_map["phenomenonTime"]
        idx_result = field_map["result"]

        no_data_value = datastream.no_data_value

        observation_records = [
            Observation(
                datastream_id=datastream_id,
                phenomenon_time=row[idx_phenomenon],
                result=(
                    no_data_value
                    if isinstance(row[idx_result], float)
                    and math.isnan(row[idx_result])
                    else row[idx_result]
                ),
            )
            for row in data.data
        ]

        if "resultQualifierCodes" in data.fields:
            idx_result_qualifier_codes = field_map["resultQualifierCodes"]
            result_qualifier_code_set = {
                code for row in data.data for code in row[idx_result_qualifier_codes]
            }
            valid_codes = set(
                principal.filter_by_permission(
                    ResultQualifier.objects.filter(
                        Q(workspace_id=datastream.thing.workspace_id)
                        | Q(workspace__isnull=True)
                    ).filter(code__in=result_qualifier_code_set),
                    "can_view",
                ).values_list("code", flat=True)
            )
            invalid_codes = result_qualifier_code_set - valid_codes
            if invalid_codes:
                raise HttpError(
                    400,
                    f"Invalid result qualifier codes: {', '.join(sorted(invalid_codes))}",
                )
            for obs, row in zip(observation_records, data.data):
                obs.result_qualifiers = row[idx_result_qualifier_codes]

        if mode == "append" and datastream.phenomenon_end_time:
            if (
                min(obs.phenomenon_time for obs in observation_records)
                <= datastream.phenomenon_end_time
            ):
                raise HttpError(
                    400,
                    "All observations must occur after the datastream's end time for append mode",
                )

        elif mode == "backfill" and datastream.phenomenon_begin_time:
            if (
                max(obs.phenomenon_time for obs in observation_records)
                >= datastream.phenomenon_begin_time
            ):
                raise HttpError(
                    400,
                    "All observations must occur before the datastream's begin time for backfill mode",
                )

        elif mode == "replace":
            start_time = min(obs.phenomenon_time for obs in observation_records)
            end_time = max(obs.phenomenon_time for obs in observation_records)
            self.bulk_delete(
                principal=principal,
                data=ObservationBulkDeleteBody(
                    phenomenon_time_start=start_time,
                    phenomenon_time_end=end_time,
                ),
                datastream_id=datastream_id,
                update_datastream_statistics=False,
            )

        try:
            Observation.objects.bulk_copy(observation_records)
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise HttpError(409, "Duplicate phenomenonTime found on this datastream.")

        if update_datastream_statistics is True:
            datastream_service.update_observation_statistics(
                datastream=datastream,
                fields=["phenomenon_begin_time", "phenomenon_end_time", "value_count"],
            )

    def bulk_delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservationBulkDeleteBody,
        datastream_id: uuid.UUID,
        update_datastream_statistics: bool = True,
    ):
        datastream = datastream_service.get_datastream_for_action(
            principal, datastream_id, action="view"
        )
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=datastream.thing.workspace_id
        )

        if not principal.has_permission(
            workspace, resource_type="Observation", permission_field="can_delete"
        ):
            raise HttpError(
                403, "You do not have permission to delete these observations"
            )

        queryset = Observation.objects.filter(datastream=datastream)

        if data.phenomenon_time_start is not None:
            queryset = queryset.filter(phenomenon_time__gte=data.phenomenon_time_start)
        if data.phenomenon_time_end is not None:
            queryset = queryset.filter(phenomenon_time__lte=data.phenomenon_time_end)

        queryset.delete()

        if update_datastream_statistics is True:
            datastream_service.update_observation_statistics(
                datastream=datastream,
                fields=["phenomenon_begin_time", "phenomenon_end_time", "value_count"],
            )

    @staticmethod
    def generate_checksum(checksum_uuid, checksum_count):
        uuid_bytes = checksum_uuid.bytes if checksum_uuid else b"\x00" * 16
        count_bytes = checksum_count.to_bytes(
            (checksum_count.bit_length() + 7) // 8 or 1, byteorder="big"
        )

        payload = uuid_bytes + count_bytes
        return hashlib.sha256(payload).hexdigest()[:16]

    def get_checksum(
        self,
        datastream: Datastream,
        phenomenon_time_start: Optional[datetime] = None,
        phenomenon_time_end: Optional[datetime] = None,
    ) -> str:
        queryset = Observation.objects.filter(datastream=datastream)

        if phenomenon_time_start is not None:
            queryset = queryset.filter(phenomenon_time__gte=phenomenon_time_start)
        if phenomenon_time_end is not None:
            queryset = queryset.filter(phenomenon_time__lte=phenomenon_time_end)

        # TODO: Can't really fix this until PostgreSQL 18 UUID v7 support
        result = queryset.aggregate(
            max_id=Max(
                Func(
                    F("id"),
                    function="CAST",
                    template="%(function)s(%(expressions)s AS text)",
                )
            ),
            count=Count("id"),
        )
        checksum_uuid = uuid.UUID(result["max_id"]) if result["max_id"] else None

        return self.generate_checksum(checksum_uuid, result["count"])
