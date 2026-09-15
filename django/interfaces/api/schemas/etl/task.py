import uuid

from typing import Optional, Any, Literal, Annotated
from pydantic import AliasPath, AliasChoices, BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Query, Field, Schema

from core.types import Unset, ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    DataConnectionResponse,
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


class EtlTaskFields(Schema):
    name: str
    description: Optional[str] = None
    task_variables: dict[str, Any] = {}


ETL_TASK_INCLUDE_RELATIONS = {
    "dataConnection": {
        "path": "data_connection",
        "bucket": "dataConnections",
        "response_schema": DataConnectionResponse,
    },
}
EtlTaskIncludeRelation = Literal[*ETL_TASK_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "id",
    "name",
    "dataConnectionId",
    "dataConnectionName",
    "workspaceId",
    "workspaceName",
    "latestRunStatus",
    "latestRunStartedAt",
    "latestRunFinishedAt",
)
EtlTaskSortByFields = Literal[*_sortby_fields, *[f"-{f}" for f in _sortby_fields]]

_property_fields = (
    "id",
    "workspaceId",
    "dataConnectionId",
    "schedule",
    "latestRun",
    "mappingCount",
    *(to_camel(name) for name in EtlTaskFields.model_fields),
)
EtlTaskPropertyName = Literal[*_property_fields]


class EtlTaskFilterFields(Schema):
    properties: Annotated[
        Optional[list[EtlTaskPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(EtlTaskPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[EtlTaskIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(EtlTaskIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class EtlTaskItemQueryParameters(EtlTaskFilterFields, BaseQueryParameters):
    pass


class EtlTaskQueryParameters(EtlTaskFilterFields, CollectionQueryParameters):
    sortby: Optional[list[EtlTaskSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    monitoring_site_id: list[uuid.UUID] = Query(
        [], description="Filter ETL tasks by monitoring_site ID."
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


class EtlTaskResponse(BaseGetResponse, EtlTaskFields):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("data_connection", "workspace_id"))
    )
    data_connection_id: uuid.UUID
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    mapping_count: int = 0

    @staticmethod
    def resolve_schedule(obj):
        return resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return resolve_latest_run(obj)


class EtlTaskPostBody(BasePostBody, EtlTaskFields):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    data_connection_id: uuid.UUID
    schedule: SchedulePostBody | None = None


class EtlTaskPatchBody(BasePatchBody, EtlTaskFields):
    schedule: SchedulePatchBody | None = None
