import uuid
from typing import Optional, Literal

from ninja import Field, Query

from core.types import Unset
from interfaces.api.schemas import (
    OrderByField,
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    ThingSummaryResponse,
    DatastreamSummaryResponse,
)
from interfaces.api.schemas.orchestration.schedule import ScheduleResponse, SchedulePostBody, SchedulePatchBody
from interfaces.api.schemas.orchestration.run import TaskRunResponse


TransformationType = Literal["rating_curve", "expression", "temporal_aggregation"]
AggregationMethod = Literal["simple_mean", "weighted_mean", "min_value", "max_value", "first_value", "last_value"]
AggregationPeriod = Literal["hourly", "daily", "weekly", "monthly"]
TimezoneType = Literal["utc", "offset", "iana"]


class DataProductTaskOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    thing_id = ("thingId", "thing_id")
    thing_name = ("thingName", "thing__name")
    workspace_id = ("workspaceId", "thing__workspace_id")
    workspace_name = ("workspaceName", "thing__workspace__name")
    latest_run_status = ("latestRunStatus", "latest_run_status")
    latest_run_started_at = ("latestRunStartedAt", "latest_run_started_at")
    latest_run_finished_at = ("latestRunFinishedAt", "latest_run_finished_at")


class DataProductTaskQueryParameters(CollectionQueryParameters):
    order_by: list[DataProductTaskOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by thing ID.", alias="thing_id"
    )
    workspace: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by workspace ID.", alias="workspace_id"
    )
    latest_run_status: list[str | Literal["null"]] = Query(
        [], description="Filter data product tasks by their most recent run status."
    )
    transformation_type: list[TransformationType] = Query(
        [], description="Filter data product tasks by transformation type."
    )
    output_datastream: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by output datastream ID.", alias="output_datastream_id"
    )
    input_datastream: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by input datastream ID.", alias="input_datastream_id"
    )
    rating_curve: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by rating curve ID.", alias="rating_curve_id"
    )
    expression: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by expression ID.", alias="expression_id"
    )


class DataProductInputMappingResponse(BaseGetResponse):
    datastream: DatastreamSummaryResponse
    variable_name: Optional[str] = None


class DataProductOutputMappingResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    transformation_type: TransformationType
    rating_curve_id: Optional[uuid.UUID] = None
    expression_id: Optional[uuid.UUID] = None
    alignment_tolerance: Optional[int] = None
    aggregation_method: Optional[AggregationMethod] = None
    aggregation_period: Optional[AggregationPeriod] = None
    aggregation_timezone_type: Optional[TimezoneType] = None
    aggregation_timezone: Optional[str] = None
    aggregation_min_coverage: Optional[float] = None
    input_mappings: list[DataProductInputMappingResponse]

    @staticmethod
    def resolve_input_mappings(obj):
        return obj.input_mappings.all()


class DataProductTaskResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing: ThingSummaryResponse
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    mappings: list[DataProductOutputMappingResponse]

    @staticmethod
    def resolve_schedule(obj):
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

    @staticmethod
    def resolve_latest_run(obj):
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

    @staticmethod
    def resolve_mappings(obj):
        return obj.mappings.all()


class DataProductInputMappingPostBody(BasePostBody):
    datastream_id: uuid.UUID
    variable_name: Optional[str] = None


class DataProductOutputMappingPostBody(BasePostBody):
    output_datastream_id: uuid.UUID
    transformation_type: TransformationType
    rating_curve_id: Optional[uuid.UUID] = None
    expression_id: Optional[uuid.UUID] = None
    alignment_tolerance: Optional[int] = None
    aggregation_method: Optional[AggregationMethod] = None
    aggregation_period: Optional[AggregationPeriod] = None
    aggregation_timezone_type: Optional[TimezoneType] = None
    aggregation_timezone: Optional[str] = None
    aggregation_min_coverage: Optional[float] = None
    input_mappings: list[DataProductInputMappingPostBody] = []


class DataProductTaskPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    schedule: SchedulePostBody | None = None
    mappings: list[DataProductOutputMappingPostBody] = []


class DataProductOutputMappingPatchBody(BasePostBody):
    output_datastream_id: uuid.UUID
    transformation_type: TransformationType
    rating_curve_id: Optional[uuid.UUID] = None
    expression_id: Optional[uuid.UUID] = None
    alignment_tolerance: Optional[int] = None
    aggregation_method: Optional[AggregationMethod] = None
    aggregation_period: Optional[AggregationPeriod] = None
    aggregation_timezone_type: Optional[TimezoneType] = None
    aggregation_timezone: Optional[str] = None
    aggregation_min_coverage: Optional[float] = None
    input_mappings: list[DataProductInputMappingPostBody] = []


class DataProductTaskPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    schedule: SchedulePatchBody | None = None
    mappings: list[DataProductOutputMappingPatchBody] = []
