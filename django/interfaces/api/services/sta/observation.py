import uuid
import math
import hashlib

from typing import Optional, Literal, get_args
from datetime import datetime
from psycopg.errors import UniqueViolation
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, Func, F, Sum
from django.db.utils import IntegrityError

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Datastream, Observation, ResultQualifier
from interfaces.api.service import APIService
from interfaces.api.services.sta.datastream import DatastreamAPIService
from interfaces.api.http.errors import BadRequestError, ConflictError, PermissionDeniedError, NotFoundError
from interfaces.api.schemas import BoundingBox, PaginatedResponse, TimeInterval
from interfaces.api.schemas.sta.observation import (
    ObservationFields,
    ObservationSortByFields,
    ObservationResponse,
    ObservationPostBody,
    ObservationBulkPostBody,
    ObservationBulkColumnarPostBody,
    ObservationBulkDeleteBody,
    ObservationColumnResponse,
    ObservationColumns,
    ObservationRowResponse,
    OBSERVATION_GROUP_FIELDS,
    OBSERVATION_GROUP_WORKSPACE_FIELD,
    OBSERVATION_INCLUDE_RELATIONS,
)

User = get_user_model()
datastream_service = DatastreamAPIService()


class ObservationAPIService(APIService):
    INCLUDE_RELATIONS = OBSERVATION_INCLUDE_RELATIONS

    def get_observation_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        datastream_id: Optional[uuid.UUID] = None,
        select_related: Optional[list[str]] = None,
    ):
        queryset = Observation.objects.annotate(
            result_qualifier_codes=F("result_qualifiers")
        ).select_related("datastream__monitoring_site")

        if select_related:
            queryset = queryset.select_related(*select_related)
        if datastream_id:
            queryset = queryset.filter(id=uid, datastream__id=datastream_id)
        else:
            queryset = queryset.filter(id=uid)

        queryset = principal.annotate_permissions(queryset)

        try:
            observation = queryset.get()
        except Observation.DoesNotExist:
            raise NotFoundError("Observation does not exist")

        if not principal.can_view(observation):
            raise NotFoundError("Observation does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(observation):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this observation"
            )

        return observation

    @classmethod
    def _include_query_hints(cls, requested_includes: set[str]) -> list[str]:
        select_paths = cls.resolve_select_related_paths(
            requested_includes, cls.INCLUDE_RELATIONS
        )
        if "workspace" in requested_includes:
            select_paths.append("datastream__monitoring_site__workspace__owner")

        return select_paths

    def _resolve_datastream_and_workspace(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        datastream_id: uuid.UUID,
    ):
        datastream = datastream_service.get_datastream_for_action(
            principal, datastream_id, action="view"
        )
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=datastream.monitoring_site.workspace_id
        )

        return datastream, workspace

    @staticmethod
    def _validate_result_qualifier_codes(
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: uuid.UUID,
        codes,
    ) -> None:
        if not codes:
            return

        valid_codes = set(
            principal.filter_by_permission(
                ResultQualifier.objects.filter(
                    Q(workspace_id=workspace_id) | Q(workspace__isnull=True)
                ).filter(name__in=codes),
                "can_view",
            ).values_list("name", flat=True)
        )
        invalid_codes = set(codes) - valid_codes
        if invalid_codes:
            raise BadRequestError(
                f"Invalid result qualifier codes: {', '.join(sorted(invalid_codes))}",
            )

    @staticmethod
    def sum_datastream_value_count(
        principal: User | ServiceAccount | AnonymousPrincipal,
        datastream_ids: list[uuid.UUID],
        bbox: Optional[BoundingBox] = None,
    ) -> int:
        """
        Exact observation count for the given datastreams (or every datastream the
        principal can view if none are given), optionally limited to datastreams whose
        monitoring site lies inside a bounding box, via Datastream's maintained value_count
        rather than a COUNT(*) over Observation.
        """

        queryset = (
            Datastream.objects.filter(id__in=datastream_ids)
            if datastream_ids
            else Datastream.objects
        )
        queryset = DatastreamAPIService.apply_site_bbox(queryset, bbox)
        queryset = principal.filter_by_permission(queryset, "can_view")

        return queryset.aggregate(total=Sum("value_count"))["total"] or 0

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        profile: Optional[str] = None,
        properties: Optional[list[str]] = None,
        include: Optional[list[str]] = None,
        bbox: Optional[BoundingBox] = None,
        datetime_interval: Optional[TimeInterval] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        queryset = Observation.objects

        datastream_ids = filtering.get("datastream_id") or []

        if "datastream_id" in filtering:
            queryset = self.apply_filters(queryset, "datastream_id", filtering["datastream_id"])

        queryset = self.apply_datetime_instant(queryset, datetime_interval, "phenomenon_time")

        if filtering.get("result_qualifier_codes"):
            code_filter = Q()
            for code in filtering["result_qualifier_codes"]:
                code_filter |= Q(result_qualifiers__contains=[code])
            queryset = queryset.filter(code_filter)

        if bbox is not None:
            queryset = queryset.filter(
                datastream_id__in=DatastreamAPIService.apply_site_bbox(
                    Datastream.objects, bbox
                ).values("id")
            )

        queryset = principal.filter_by_permission(queryset, "can_view")

        count = (
            self.resolve_count(queryset)
            if datetime_interval is not None or filtering.get("result_qualifier_codes")
            else self.sum_datastream_value_count(principal, datastream_ids, bbox)
        )

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

        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(ObservationSortByFields)),
            default_sortby=("datastream_id", "phenomenon_time"),
        )

        select_paths = ["datastream__monitoring_site"]
        if requested_includes:
            select_paths.extend(self._include_query_hints(requested_includes))

        queryset = queryset.select_related(*select_paths)
        queryset, meta = self.apply_pagination(queryset, offset, limit, count=count)
        response["X-Checksum"] = self.generate_checksum(checksum_uuid, meta.number_matched)

        if profile in ("row", "column"):
            return self.grouped_values(queryset, meta, profile, properties, requested_includes)

        observations = list(queryset.all())
        return {
            "data": [
                ObservationResponse.model_validate(observation)
                for observation in observations
            ],
            "meta": meta,
            "included": self.resolve_includes(
                observations, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def grouped_values(
        self,
        queryset,
        meta,
        profile: Literal["row", "column"],
        properties: Optional[list[str]],
        requested_includes: set[str],
    ):
        """
        A page of observations as groups of their selected property values per datastream, in the order each
        datastream first appears on the page, with each group's values in page order. Without included resources,
        only the selected properties are read; with them, the observations are read to resolve what they include.
        """

        selected = [name for name in OBSERVATION_GROUP_FIELDS if properties is None or name in properties]
        with_workspace = properties is None or "workspaceId" in properties
        included = None

        if requested_includes:
            observations = list(queryset)
            entries = (
                (
                    observation.datastream_id,
                    observation.datastream.monitoring_site.workspace_id if with_workspace else None,
                    [getattr(observation, OBSERVATION_GROUP_FIELDS[name]) for name in selected],
                )
                for observation in observations
            )
            included = self.resolve_includes(observations, requested_includes, self.INCLUDE_RELATIONS)
        else:
            lookups = [
                "datastream_id",
                *([OBSERVATION_GROUP_WORKSPACE_FIELD] if with_workspace else []),
                *(OBSERVATION_GROUP_FIELDS[name] for name in selected),
            ]
            offset = 2 if with_workspace else 1
            entries = (
                (row[0], row[1] if with_workspace else None, list(row[offset:]))
                for row in queryset.values_list(*lookups)
            )

        groups: dict[uuid.UUID, tuple[Optional[uuid.UUID], list[list]]] = {}
        for datastream_id, workspace_id, values in entries:
            groups.setdefault(datastream_id, (workspace_id, []))[1].append(values)

        returned = sum(len(rows) for _, rows in groups.values())

        if profile == "row":
            data = [
                ObservationRowResponse(datastream_id=datastream_id, workspace_id=workspace_id, fields=selected, rows=rows)
                for datastream_id, (workspace_id, rows) in groups.items()
            ]
            return PaginatedResponse[ObservationRowResponse](data=data, meta=meta, included=included, returned=returned)

        data = [
            ObservationColumnResponse(
                datastream_id=datastream_id,
                workspace_id=workspace_id,
                columns=ObservationColumns(**{name: list(column) for name, column in zip(selected, zip(*rows))}),
            )
            for datastream_id, (workspace_id, rows) in groups.items()
        ]

        return PaginatedResponse[ObservationColumnResponse](data=data, meta=meta, included=included, returned=returned)

    def get_item(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        datastream_id: Optional[uuid.UUID] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_related = (
            self._include_query_hints(requested_includes)
            if requested_includes
            else None
        )

        observation = self.get_observation_for_action(
            principal=principal,
            uid=uid,
            action="view",
            datastream_id=datastream_id,
            select_related=select_related,
        )

        return {
            "data": ObservationResponse.model_validate(observation),
            "included": self.resolve_includes(
                [observation], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ObservationPostBody,
        datastream_id: uuid.UUID,
        update_datastream_statistics: bool = True,
    ):
        datastream, workspace = self._resolve_datastream_and_workspace(
            principal, datastream_id
        )

        if not principal.can_create("Observation", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to create this observation"
            )

        observation = Observation(
            pk=data.id,
            datastream=datastream,
            **data.dict(include=set(ObservationFields.model_fields.keys()), exclude=["result_qualifier_codes"]),
        )
        observation.full_clean()

        try:
            observation.save()
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise ConflictError("Duplicate phenomenonTime or ID found on this datastream.")

        self._validate_result_qualifier_codes(
            principal, datastream.monitoring_site.workspace_id, data.result_qualifier_codes
        )
        if data.result_qualifier_codes:
            observation.result_qualifiers = data.result_qualifier_codes
            observation.save(update_fields=["result_qualifiers"])

        if update_datastream_statistics is True:
            datastream_service.update_observation_statistics(
                datastream=datastream,
                fields=["phenomenon_begin_time", "phenomenon_end_time", "value_count"],
            )

        return {"id": observation.id}

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        datastream_id: Optional[uuid.UUID] = None,
        update_datastream_statistics: bool = True,
    ):
        observation = self.get_observation_for_action(
            principal=principal,
            uid=uid,
            action="delete",
            datastream_id=datastream_id,
        )
        datastream = observation.datastream
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
        datastream, workspace = self._resolve_datastream_and_workspace(
            principal, datastream_id
        )

        if not principal.can_create("Observation", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to create these observations"
            )

        required_fields = {"phenomenonTime", "result"}
        if not required_fields.issubset(set(data.fields)):
            raise BadRequestError("Missing required observation fields")

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
            self._validate_result_qualifier_codes(
                principal, datastream.monitoring_site.workspace_id, result_qualifier_code_set
            )
            for obs, row in zip(observation_records, data.data):
                obs.result_qualifiers = row[idx_result_qualifier_codes]

        if mode == "append" and datastream.phenomenon_end_time:
            if (
                min(obs.phenomenon_time for obs in observation_records)
                <= datastream.phenomenon_end_time
            ):
                raise BadRequestError(
                    "All observations must occur after the datastream's end time for append mode",
                )

        elif mode == "backfill" and datastream.phenomenon_begin_time:
            if (
                max(obs.phenomenon_time for obs in observation_records)
                >= datastream.phenomenon_begin_time
            ):
                raise BadRequestError(
                    "All observations must occur before the datastream's begin time for backfill mode",
                )

        elif mode == "replace":
            start_time = min(obs.phenomenon_time for obs in observation_records)
            end_time = max(obs.phenomenon_time for obs in observation_records)
            self.bulk_delete(
                principal=principal,
                data=ObservationBulkDeleteBody(
                    datastream_id=datastream_id,
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
            raise ConflictError("Duplicate phenomenonTime found on this datastream.")

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
        datastream, workspace = self._resolve_datastream_and_workspace(
            principal, datastream_id
        )

        if not principal.has_permission(
            workspace, resource_type="Observation", permission_field="can_delete"
        ):
            raise PermissionDeniedError(
                "You do not have permission to delete these observations"
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
