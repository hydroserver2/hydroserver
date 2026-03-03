import uuid
from typing import Any, Literal, Optional
from datetime import datetime
from ninja import Schema, Field, Query
from interfaces.api.types import ISODatetime
from interfaces.api.schemas import BaseGetResponse, BasePostBody, BasePatchBody, CollectionQueryParameters
from interfaces.api.schemas import WorkspaceSummaryResponse
from .data_connection import DataConnectionSummaryResponse
from .orchestration_system import OrchestrationSystemSummaryResponse
from .run import TaskRunResponse


_order_by_fields = (
    "name",
    "orchestrationSystemType",
    "latestRunStatus",
    "latestRunStartedAt",
    "latestRunFinishedAt",
    "nextRunAt",
    "paused",
    "startTime",
    "dataConnectionType",
    "dataConnectionExtractorType",
    "dataConnectionTransformerType",
    "dataConnectionLoaderType"
)

TaskOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class TaskQueryParameters(CollectionQueryParameters):
    order_by: list[TaskOrderByFields] | None = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID] = Query(
        [], description="Filter by workspace ID."
    )
    data_connection_id: list[uuid.UUID] = Query([], description="Filter by data connection ID.")
    orchestration_system_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter by orchestration system ID."
    )
    orchestration_system__type: list[str] = Query([], description="Filter by orchestration system type.")
    latest_run_status: list[str | Literal["null"]] = Query(
        [], description="Filters tasks by the status of their most recent run."
    )
    latest_run_started_at__lte: ISODatetime | None = Query(
        None, description="Filters for tasks whose most recent run started on or before this date and time.",
        alias="latest_run_started_at_max"
    )
    latest_run_started_at__gte: ISODatetime | None = Query(
        None, description="Filters for tasks whose most recent run started on or after this date and time.",
        alias="latest_run_started_at_min"
    )
    latest_run_finished_at__lte: ISODatetime | None = Query(
        None, description="Filters for tasks whose most recent run finished on or before this date and time.",
        alias="latest_run_finished_at_max"
    )
    latest_run_finished_at__gte: ISODatetime | None = Query(
        None, description="Filters for tasks whose most recent run finished on or after this date and time.",
        alias="latest_run_finished_at_min"
    )
    next_run_at__lte: ISODatetime | None = Query(
        None, description="Filters for scheduled tasks with a next run on or before this value.",
        alias="next_run_at_max"
    )
    next_run_at__gte: ISODatetime | None = Query(
        None, description="Filters for scheduled tasks with a next run on or after this value.",
        alias="next_run_at_min"
    )
    paused: bool | None = Query(
        None, description="Filters by the paused status of the task."
    )
    periodic_task__start_time__lte: ISODatetime | None = Query(
        None, description="Filters for scheduled tasks with a start time on or before this value.",
        alias="start_time_max"
    )
    periodic_task__start_time__gte: ISODatetime | None = Query(
        None, description="Filters for scheduled tasks with a start time on or after this value.",
        alias="start_time_min"
    )
    data_connection__data_connection_type: list[str] = Query(
        [], description="Filters by the type of the data connection.", alias="data_connection_type"
    )
    data_connection__extractor_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the extractor type of the data connection.", alias="extractor_type"
    )
    data_connection__transformer_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the transformer type of the data connection.", alias="transformer_type"
    )
    data_connection__loader_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the loader type of the data connection.", alias="loader_type"
    )
    mappings__source_identifier: list[str | Literal["null"]] = Query(
        [], description="Filters by source identifiers associated with the task.",
        alias="source_identifier"
    )
    mappings__paths__target_identifier: list[str | Literal["null"]] = Query(
        [], description="Filters by target identifiers associated with the task.",
        alias="target_identifier"
    )
    expand_related: bool | None = None


class TaskScheduleFields(Schema):
    paused: bool
    start_time: datetime | None = None
    next_run_at: datetime | None = None
    crontab: str | None = None
    interval: int | None = Field(None, ge=1)
    interval_period: Literal["minutes", "hours", "days"] | None = None


class TaskScheduleResponse(BaseGetResponse, TaskScheduleFields):
    pass


class TaskSchedulePostBody(BasePostBody, TaskScheduleFields):
    pass


class TaskSchedulePatchBody(BasePatchBody, TaskScheduleFields):
    pass


class TaskMappingPathFields(Schema):
    target_identifier: str
    data_transformations: list[Any] = Field(default_factory=list)


class TaskMappingPathResponse(BaseGetResponse, TaskMappingPathFields):
    pass


class TaskMappingPathPostBody(BasePostBody, TaskMappingPathResponse):
    pass


class TaskMappingFields(Schema):
    source_identifier: str


class TaskMappingResponse(BaseGetResponse, TaskMappingFields):
    paths: list[TaskMappingPathResponse]


class TaskMappingPostBody(BasePostBody, TaskMappingFields):
    paths: list[TaskMappingPathPostBody]


class TaskFields(Schema):
    name: str
    extractor_variables: dict[str, Any] = Field(default_factory=dict)
    transformer_variables: dict[str, Any] = Field(default_factory=dict)
    loader_variables: dict[str, Any] = Field(default_factory=dict)


class TaskSummaryResponse(BaseGetResponse, TaskFields):
    id: uuid.UUID
    workspace_id: uuid.UUID
    data_connection_id: uuid.UUID
    orchestration_system_id: uuid.UUID
    schedule: TaskScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    mappings: list[TaskMappingResponse]


class TaskDetailResponse(BaseGetResponse, TaskFields):
    id: uuid.UUID
    workspace: WorkspaceSummaryResponse
    data_connection: DataConnectionSummaryResponse
    orchestration_system: OrchestrationSystemSummaryResponse
    schedule: TaskScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    mappings: list[TaskMappingResponse]


class TaskPostBody(BasePostBody, TaskFields):
    id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    data_connection_id: uuid.UUID
    orchestration_system_id: uuid.UUID
    schedule: TaskSchedulePostBody | None = None
    mappings: list[TaskMappingPostBody]


class TaskPatchBody(BasePatchBody, TaskFields):
    data_connection_id: uuid.UUID | None = None
    orchestration_system_id: uuid.UUID | None = None
    schedule: TaskSchedulePatchBody | None = None
    mappings: list[TaskMappingPostBody] | None = None
