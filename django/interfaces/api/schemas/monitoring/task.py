import uuid

from typing import Optional, Literal, Annotated
from pydantic import AliasPath, AliasChoices, BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Query, Field, Schema

from core.types import Unset
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    MonitoringSiteResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.orchestration.schedule import (
    ScheduleResponse,
    SchedulePostBody,
    SchedulePatchBody,
    resolve_schedule,
)
from interfaces.api.schemas.orchestration.run import TaskRunResponse, resolve_latest_run


class MonitoringTaskFields(Schema):
    name: str
    description: Optional[str] = None


MONITORING_TASK_INCLUDE_RELATIONS = {
    "monitoringSite": {
        "path": "monitoring_site",
        "bucket": "monitoringSites",
        "response_schema": MonitoringSiteResponse,
    },
}
MonitoringTaskIncludeRelation = Literal[*MONITORING_TASK_INCLUDE_RELATIONS.keys()]

_order_by_fields = (
    "id",
    "name",
    "monitoringSiteId",
    "monitoringSiteName",
    "workspaceId",
    "workspaceName",
    "latestRunStatus",
    "latestRunStartedAt",
    "latestRunFinishedAt",
)
MonitoringTaskOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    "monitoringSiteId",
    "schedule",
    "latestRun",
    "ruleTypeCounts",
    "recipients",
    *(to_camel(name) for name in MonitoringTaskFields.model_fields),
)
MonitoringTaskPropertyName = Literal[*_property_fields]


class MonitoringTaskFilterFields(Schema):
    properties: Annotated[
        Optional[list[MonitoringTaskPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringTaskPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[MonitoringTaskIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringTaskIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class MonitoringTaskItemQueryParameters(MonitoringTaskFilterFields, BaseQueryParameters):
    pass


class MonitoringTaskQueryParameters(MonitoringTaskFilterFields, CollectionQueryParameters):
    order_by: Optional[list[MonitoringTaskOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    monitoring_site: list[uuid.UUID] = Query(
        [], description="Filter monitoring tasks by monitoring_site ID.", alias="monitoring_site_id"
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


class MonitoringTaskResponse(BaseGetResponse, MonitoringTaskFields):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("monitoring_site", "workspace_id"))
    )
    monitoring_site_id: uuid.UUID
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    rule_type_counts: dict[str, int] = {}
    recipients: list[str] = []

    @staticmethod
    def resolve_schedule(obj):
        return resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return resolve_latest_run(obj)

    @staticmethod
    def resolve_recipients(obj):
        if not hasattr(obj.recipients, "all"):
            return obj.recipients
        return [r.email for r in obj.recipients.all()]


class MonitoringTaskPostBody(BasePostBody, MonitoringTaskFields):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    monitoring_site_id: uuid.UUID
    schedule: SchedulePostBody | None = None
    recipients: list[str] = []


class MonitoringTaskPatchBody(BasePatchBody, MonitoringTaskFields):
    schedule: SchedulePatchBody | None = None
    recipients: list[str] = []
