import uuid

from datetime import datetime
from typing import Optional, Literal, Union, Annotated
from pydantic import EmailStr, BeforeValidator, WithJsonSchema
from ninja import Field, Query, Schema
from django.utils import timezone

from core.types import Unset
from processing.orchestration.attention import attention_filter, latest_run_status_subquery
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    WorkspaceResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.orchestration.schedule import (
    ScheduleResponse,
    SchedulePostBody,
    SchedulePatchBody,
    resolve_schedule,
)


DATA_CONNECTION_INCLUDE_RELATIONS = {
    "workspace": {
        "path": "workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
}
DataConnectionIncludeRelation = Literal[*DATA_CONNECTION_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "id",
    "name",
    "timestampKey",
    "timestampFormat",
    "timezoneType",
    "timezone",
    "workspaceId",
    "workspaceName",
)

DataConnectionSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "name",
    "description",
    "sourceUrl",
    "authHeaderName",
    "authHeaderValue",
    "timezoneType",
    "timezone",
    "workspaceId",
    "payload",
    "placeholderVariables",
    "notification",
    "taskCount",
    "taskAttentionCount",
)
DataConnectionPropertyName = Literal[*_property_fields]


class DataConnectionFilterFields(Schema):
    properties: Annotated[
        Optional[list[DataConnectionPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataConnectionPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[DataConnectionIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataConnectionIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class DataConnectionItemQueryParameters(DataConnectionFilterFields, BaseQueryParameters):
    pass


class DataConnectionQueryParameters(DataConnectionFilterFields, CollectionQueryParameters):
    sortby: Optional[list[DataConnectionSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    workspace: list[uuid.UUID] = Query(
        [], description="Filter data connections by workspace ID.", alias="workspace_id"
    )
    payload_type: list[str] = Query(
        [], description="Filter data connections by payload type."
    )


DataIngestionWindowAnchorType = Literal["latest_observation_timestamp", "run_time", "fixed_timestamp"]
DataIngestionWindowLookbackUnits = Literal["minutes", "hours", "days"]


class DataIngestionWindowBoundaryResponse(BaseGetResponse):
    anchor: Optional[DataIngestionWindowAnchorType] = None
    lookback: Optional[int] = None
    lookback_units: Optional[DataIngestionWindowLookbackUnits] = None
    timestamp: Optional[datetime] = None


class DataIngestionWindowResponse(BaseGetResponse):
    start: Optional[DataIngestionWindowBoundaryResponse] = None
    end: Optional[DataIngestionWindowBoundaryResponse] = None


class DataIngestionWindowBoundaryPostBody(BasePostBody):
    anchor: Optional[DataIngestionWindowAnchorType] = None
    lookback: Optional[int] = None
    lookback_units: Optional[DataIngestionWindowLookbackUnits] = None
    timestamp: Optional[datetime] = None


class DataIngestionWindowPostBody(BasePostBody):
    start: Optional[DataIngestionWindowBoundaryPostBody] = None
    end: Optional[DataIngestionWindowBoundaryPostBody] = None


def _resolve_data_ingestion_window(obj):
    start = end = None

    if obj.data_ingestion_window_start_anchor:
        start = {
            "anchor": obj.data_ingestion_window_start_anchor,
            "lookback": obj.data_ingestion_window_start_lookback,
            "lookback_units": obj.data_ingestion_window_start_lookback_unit,
            "timestamp": obj.data_ingestion_window_start_timestamp,
        }

    if obj.data_ingestion_window_end_anchor:
        end = {
            "anchor": obj.data_ingestion_window_end_anchor,
            "lookback": obj.data_ingestion_window_end_lookback,
            "lookback_units": obj.data_ingestion_window_end_lookback_unit,
            "timestamp": obj.data_ingestion_window_end_timestamp,
        }

    if start is None and end is None:
        return None

    return {"start": start, "end": end}


class CSVPayloadResponse(BaseGetResponse):
    payload_type: Literal["CSV"] = Field(alias="type")
    timestamp_key: str
    timestamp_format: Optional[str] = None
    header_row: Optional[int] = None
    data_start_row: Optional[int] = None
    delimiter: Optional[Literal[",", "|", "\t", ";", " "]] = Field(None, max_length=1)
    data_ingestion_window: Optional[DataIngestionWindowResponse] = None
    resolve_data_ingestion_window = staticmethod(_resolve_data_ingestion_window)


class CSVPayloadPostBody(BasePostBody, CSVPayloadResponse):
    header_row: int
    data_start_row: int
    delimiter: Literal[",", "|", "\t", ";", " "] = Field(max_length=1)
    data_ingestion_window: Optional[DataIngestionWindowPostBody] = None


class CSVPayloadPatchBody(BasePatchBody, CSVPayloadResponse):
    data_ingestion_window: Optional[DataIngestionWindowPostBody] = None


class JSONPayloadResponse(BaseGetResponse):
    payload_type: Literal["JSON"] = Field(alias="type")
    timestamp_key: str
    timestamp_format: Optional[str] = None
    jmespath: Optional[str] = None
    data_ingestion_window: Optional[DataIngestionWindowResponse] = None
    resolve_data_ingestion_window = staticmethod(_resolve_data_ingestion_window)


class JSONPayloadPostBody(BasePostBody, JSONPayloadResponse):
    jmespath: str
    data_ingestion_window: Optional[DataIngestionWindowPostBody] = None


class JSONPayloadPatchBody(BasePatchBody, JSONPayloadResponse):
    data_ingestion_window: Optional[DataIngestionWindowPostBody] = None


class PayloadPatchBody(BasePatchBody):
    payload_type: Optional[Literal["CSV", "JSON"]] = Field(None, alias="type")
    timestamp_key: Optional[str] = None
    timestamp_format: Optional[str] = None
    header_row: Optional[int] = None
    data_start_row: Optional[int] = None
    delimiter: Optional[Literal[",", "|", "\t", ";", " "]] = Field(None, max_length=1)
    jmespath: Optional[str] = None
    data_ingestion_window: Optional[DataIngestionWindowPostBody] = None


class PlaceholderVariableResponse(BaseGetResponse):
    name: str
    variable_type: Literal[
        "run_time", "latest_observation_timestamp", "per_task", "window_start", "window_end"
    ] = Field(alias="type")
    timestamp_format: Optional[str] = None


class PlaceholderVariablePostBody(BasePostBody, PlaceholderVariableResponse):
    ...


class PlaceholderVariablePatchBody(BasePatchBody, PlaceholderVariableResponse):
    ...


class NotificationResponse(BaseGetResponse):
    schedule: ScheduleResponse | None = None
    recipient_emails: list[EmailStr]

    @staticmethod
    def resolve_schedule(obj):
        return resolve_schedule(obj)

    @staticmethod
    def resolve_recipient_emails(obj):
        return obj.recipients.values_list("email", flat=True)


class NotificationPostBody(BasePostBody):
    schedule: SchedulePostBody
    recipient_emails: list[EmailStr]


class NotificationPatchBody(BasePatchBody):
    recipient_emails: list[EmailStr]
    schedule: SchedulePatchBody | Unset = Unset


class DataConnectionResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    source_url: str
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None
    timezone_type: Optional[Literal["offset", "iana"]] = None
    timezone: Optional[str] = None
    workspace_id: uuid.UUID
    payload: Union[CSVPayloadResponse, JSONPayloadResponse]
    placeholder_variables: list[PlaceholderVariableResponse]
    notification: Optional[NotificationResponse] = None
    task_count: int = 0
    task_attention_count: int = 0

    @staticmethod
    def resolve_notification(obj):
        try:
            return obj.notification
        except AttributeError:
            return None

    @staticmethod
    def resolve_task_count(obj):
        return getattr(obj, "task_count", None) or 0

    @staticmethod
    def resolve_task_attention_count(obj):
        if hasattr(obj, "task_attention_count"):
            return obj.task_attention_count or 0

        now = timezone.now()

        return obj.etl_tasks.annotate(
            latest_run_status=latest_run_status_subquery()
        ).filter(attention_filter(now)).count()


class DataConnectionPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    source_url: str
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None
    workspace_id: uuid.UUID
    timezone_type: Optional[Literal["offset", "iana"]] = None
    timezone: Optional[str] = None
    payload: Union[CSVPayloadPostBody, JSONPayloadPostBody]
    placeholder_variables: list[PlaceholderVariablePostBody]
    notification: NotificationPostBody | None = None


class DataConnectionPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    source_url: str
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None
    timezone_type: Optional[Literal["offset", "iana"]] = None
    timezone: Optional[str] = None
    payload: PayloadPatchBody
    placeholder_variables: list[PlaceholderVariablePatchBody]
    notification: NotificationPatchBody | None | Unset = Unset
