import uuid
from typing import Optional, Any, Literal

from ninja import Query, Field

from core.types import Unset, ISODatetime
from interfaces.api.schemas import (
    OrderByField,
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    DatastreamSummaryResponse,
)
from interfaces.api.schemas.orchestration.schedule import ScheduleResponse, SchedulePostBody, SchedulePatchBody
from interfaces.api.schemas.orchestration.run import TaskRunResponse
from interfaces.api.schemas.etl.data_connection import DataConnectionResponse


class EtlTaskOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    data_connection_id = ("dataConnectionId", "data_connection_id")
    data_connection_name = ("dataConnectionName", "data_connection__name")
    workspace_id = ("workspaceId", "data_connection__workspace_id")
    workspace_name = ("workspaceName", "data_connection__workspace__name")
    latest_run_status = ("latestRunStatus", "latest_run_status")
    latest_run_started_at = ("latestRunStartedAt", "latest_run_started_at")
    latest_run_finished_at = ("latestRunFinishedAt", "latest_run_finished_at")


class EtlTaskQueryParameters(CollectionQueryParameters):
    order_by: list[EtlTaskOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing_id: list[uuid.UUID] = Query(
        [], description="Filter ETL tasks by thing ID."
    )
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter ETL tasks by workspace ID."
    )
    data_connection_id: list[uuid.UUID] = Query(
        [], description="Filter ETL tasks by data connection ID."
    )
    latest_run_status: list[str | Literal["null"]] = Query(
        [], description="Filter ETL tasks by their most recent run status."
    )
    latest_run_started_at_min: ISODatetime | None = Query(
        None, description="Filter tasks whose latest run started on or after this datetime."
    )
    latest_run_started_at_max: ISODatetime | None = Query(
        None, description="Filter tasks whose latest run started on or before this datetime."
    )
    latest_run_finished_at_min: ISODatetime | None = Query(
        None, description="Filter tasks whose latest run finished on or after this datetime."
    )
    latest_run_finished_at_max: ISODatetime | None = Query(
        None, description="Filter tasks whose latest run finished on or before this datetime."
    )
    expand_related: Optional[bool] = None


class EtlDataMappingResponse(BaseGetResponse):
    source_identifier: str
    target_datastream: DatastreamSummaryResponse


class EtlDataMappingPostBody(BasePostBody):
    source_identifier: str
    target_datastream_id: uuid.UUID


class EtlDataMappingPatchBody(BasePatchBody):
    source_identifier: str
    target_datastream_id: uuid.UUID


def _resolve_schedule(obj):
    if not hasattr(obj, "periodic_task"):
        return getattr(obj, "schedule", None)

    pt = obj.periodic_task
    if not pt:
        return None

    ct = pt.crontab

    return {
        "enabled": pt.enabled,
        "start_time": pt.start_time,
        "crontab": f"{ct.minute} {ct.hour} {ct.day_of_month} {ct.month_of_year} {ct.day_of_week}" if ct else None,
        "interval": pt.interval.every if pt.interval else None,
        "interval_period": pt.interval.period if pt.interval else None,
        "next_run_at": obj.next_run_at,
    }


def _resolve_latest_run(obj):
    if not hasattr(obj, "latest_run_id"):
        return getattr(obj, "latest_run", None)

    if not getattr(obj, "latest_run_id", None):
        return None

    return {
        "id": obj.latest_run_id,
        "status": obj.latest_run_status,
        "started_at": obj.latest_run_started_at,
        "finished_at": obj.latest_run_finished_at,
        "message": obj.latest_run_message,
        "result": obj.latest_run_result,
    }


class EtlTaskSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    workspace_id: uuid.UUID
    data_connection_id: uuid.UUID
    task_variables: dict[str, Any]
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None

    @staticmethod
    def resolve_workspace_id(obj):
        if not hasattr(obj, "data_connection") or not hasattr(obj.data_connection, "workspace_id"):
            return getattr(obj, "workspace_id", None)
        return obj.data_connection.workspace_id

    @staticmethod
    def resolve_schedule(obj):
        return _resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return _resolve_latest_run(obj)


class EtlTaskDetailResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    task_variables: dict[str, Any]
    data_connection: DataConnectionResponse
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    mappings: list[EtlDataMappingResponse]

    @staticmethod
    def resolve_schedule(obj):
        return _resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return _resolve_latest_run(obj)

    @staticmethod
    def resolve_mappings(obj):
        if not hasattr(obj, "etl_mappings"):
            return getattr(obj, "mappings", [])
        return obj.etl_mappings.all()


class EtlTaskPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    data_connection_id: uuid.UUID
    task_variables: dict[str, Any] = {}
    schedule: SchedulePostBody | None = None
    mappings: list[EtlDataMappingPostBody] = []


class EtlTaskPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    task_variables: dict[str, Any]
    schedule: SchedulePatchBody | None = None
    mappings: list[EtlDataMappingPatchBody]
