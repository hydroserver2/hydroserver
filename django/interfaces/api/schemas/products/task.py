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
)
from interfaces.api.schemas.orchestration.schedule import ScheduleResponse, SchedulePostBody, SchedulePatchBody
from interfaces.api.schemas.orchestration.run import TaskRunResponse
from interfaces.api.schemas.products.transformation import (
    RatingCurveTransformationSummaryResponse,
    ExpressionTransformationSummaryResponse,
    CompositeExpressionTransformationSummaryResponse,
    AggregationTransformationSummaryResponse,
    RatingCurveTransformationResponse,
    ExpressionTransformationResponse,
    CompositeExpressionTransformationResponse,
    AggregationTransformationResponse,
)


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
    transformation_type: list[str] = Query(
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
    expand_related: Optional[bool] = None


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


class DataProductTaskSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    workspace_id: uuid.UUID
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    rating_curve_transformations: list[RatingCurveTransformationSummaryResponse]
    expression_transformations: list[ExpressionTransformationSummaryResponse]
    composite_expression_transformations: list[CompositeExpressionTransformationSummaryResponse]
    aggregation_transformations: list[AggregationTransformationSummaryResponse]

    @staticmethod
    def resolve_workspace_id(obj):
        if not hasattr(obj, "thing") or not hasattr(obj.thing, "workspace_id"):
            return getattr(obj, "workspace_id", None)
        return obj.thing.workspace_id

    @staticmethod
    def resolve_schedule(obj):
        return _resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return _resolve_latest_run(obj)

    @staticmethod
    def resolve_rating_curve_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "rating_curve_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "rating_curve"]

    @staticmethod
    def resolve_expression_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "expression_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "expression"]

    @staticmethod
    def resolve_composite_expression_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "composite_expression_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "composite_expression"]

    @staticmethod
    def resolve_aggregation_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "aggregation_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "aggregation"]


class DataProductTaskDetailResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing: ThingSummaryResponse
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    rating_curve_transformations: list[RatingCurveTransformationResponse]
    expression_transformations: list[ExpressionTransformationResponse]
    composite_expression_transformations: list[CompositeExpressionTransformationResponse]
    aggregation_transformations: list[AggregationTransformationResponse]

    @staticmethod
    def resolve_schedule(obj):
        return _resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return _resolve_latest_run(obj)

    @staticmethod
    def resolve_rating_curve_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "rating_curve_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "rating_curve"]

    @staticmethod
    def resolve_expression_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "expression_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "expression"]

    @staticmethod
    def resolve_composite_expression_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "composite_expression_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "composite_expression"]

    @staticmethod
    def resolve_aggregation_transformations(obj):
        if not hasattr(obj, "transformations"):
            return getattr(obj, "aggregation_transformations", [])
        return [t for t in obj.transformations.all() if t.transformation_type == "aggregation"]


class DataProductTaskPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    schedule: SchedulePostBody | None = None


class DataProductTaskPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    schedule: SchedulePatchBody | None = None
