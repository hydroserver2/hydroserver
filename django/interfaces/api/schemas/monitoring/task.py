import uuid
from typing import Optional, Literal
from collections import defaultdict

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
from interfaces.api.schemas.monitoring.rule import MonitoredDatastreamSummaryResponse, MonitoredDatastreamResponse


class MonitoringTaskOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    thing_id = ("thingId", "thing_id")
    thing_name = ("thingName", "thing__name")
    workspace_id = ("workspaceId", "thing__workspace_id")
    workspace_name = ("workspaceName", "thing__workspace__name")
    latest_run_status = ("latestRunStatus", "latest_run_status")
    latest_run_started_at = ("latestRunStartedAt", "latest_run_started_at")
    latest_run_finished_at = ("latestRunFinishedAt", "latest_run_finished_at")


class MonitoringTaskQueryParameters(CollectionQueryParameters):
    order_by: list[MonitoringTaskOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing: list[uuid.UUID] = Query(
        [], description="Filter monitoring tasks by thing ID.", alias="thing_id"
    )
    workspace: list[uuid.UUID] = Query(
        [], description="Filter monitoring tasks by workspace ID.", alias="workspace_id"
    )
    latest_run_status: list[str | Literal["null"]] = Query(
        [], description="Filter monitoring tasks by their most recent run status."
    )
    datastream: list[uuid.UUID] = Query(
        [], description="Filter monitoring tasks by datastream ID.", alias="datastream_id"
    )
    rule_type: list[str] = Query(
        [], description="Filter monitoring tasks by rule type."
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


class MonitoringTaskSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    workspace_id: uuid.UUID
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    monitored_datastreams: list[MonitoredDatastreamSummaryResponse]
    recipients: list[str]

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
    def resolve_monitored_datastreams(obj):
        if not hasattr(obj, "rules"):
            return getattr(obj, "monitored_datastreams", [])
        groups = defaultdict(list)
        for rule in obj.rules.all():
            groups[rule.datastream_id].append(rule)
        return [
            {"datastream_id": datastream_id, "rules": rules}
            for datastream_id, rules in groups.items()
        ]

    @staticmethod
    def resolve_recipients(obj):
        if not hasattr(obj.recipients, "all"):
            return obj.recipients
        return [r.email for r in obj.recipients.all()]


class MonitoringTaskDetailResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing: ThingSummaryResponse
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    monitored_datastreams: list[MonitoredDatastreamResponse]
    recipients: list[str]

    @staticmethod
    def resolve_schedule(obj):
        return _resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return _resolve_latest_run(obj)

    @staticmethod
    def resolve_monitored_datastreams(obj):
        if not hasattr(obj, "rules"):
            return getattr(obj, "monitored_datastreams", [])
        groups = defaultdict(list)
        for rule in obj.rules.all():
            groups[rule.datastream_id].append(rule)
        return [
            {"datastream": rules[0].datastream, "rules": rules}
            for rules in groups.values()
        ]

    @staticmethod
    def resolve_recipients(obj):
        if not hasattr(obj.recipients, "all"):
            return obj.recipients
        return [r.email for r in obj.recipients.all()]


class MonitoringTaskPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    schedule: SchedulePostBody | None = None
    recipients: list[str] = []


class MonitoringTaskPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    schedule: SchedulePatchBody | None = None
    recipients: list[str] = []
