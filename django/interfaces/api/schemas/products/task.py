import uuid

from typing import Optional, Literal, Annotated
from pydantic import AliasPath, AliasChoices, BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Field, Query, Schema

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


class DataProductTaskFields(Schema):
    name: str
    description: Optional[str] = None


DATA_PRODUCT_TASK_INCLUDE_RELATIONS = {
    "monitoringSite": {
        "path": "monitoring_site",
        "bucket": "monitoringSites",
        "response_schema": MonitoringSiteResponse,
    },
}
DataProductTaskIncludeRelation = Literal[*DATA_PRODUCT_TASK_INCLUDE_RELATIONS.keys()]

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
DataProductTaskOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    "monitoringSiteId",
    "schedule",
    "latestRun",
    "transformationTypes",
    *(to_camel(name) for name in DataProductTaskFields.model_fields),
)
DataProductTaskPropertyName = Literal[*_property_fields]


class DataProductTaskFilterFields(Schema):
    properties: Annotated[
        Optional[list[DataProductTaskPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataProductTaskPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[DataProductTaskIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataProductTaskIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class DataProductTaskItemQueryParameters(DataProductTaskFilterFields, BaseQueryParameters):
    pass


class DataProductTaskQueryParameters(DataProductTaskFilterFields, CollectionQueryParameters):
    order_by: Optional[list[DataProductTaskOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    monitoring_site: list[uuid.UUID] = Query(
        [], description="Filter data product tasks by monitoring_site ID.", alias="monitoring_site_id"
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


class DataProductTaskResponse(BaseGetResponse, DataProductTaskFields):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ..., validation_alias=AliasChoices("workspaceId", AliasPath("monitoring_site", "workspace_id"))
    )
    monitoring_site_id: uuid.UUID
    schedule: ScheduleResponse | None = None
    latest_run: TaskRunResponse | None = None
    transformation_types: list[str] = []

    @staticmethod
    def resolve_schedule(obj):
        return resolve_schedule(obj)

    @staticmethod
    def resolve_latest_run(obj):
        return resolve_latest_run(obj)


class DataProductTaskPostBody(BasePostBody, DataProductTaskFields):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    monitoring_site_id: uuid.UUID
    schedule: SchedulePostBody | None = None


class DataProductTaskPatchBody(BasePatchBody, DataProductTaskFields):
    schedule: SchedulePatchBody | None = None
