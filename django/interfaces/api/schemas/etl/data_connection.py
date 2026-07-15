import uuid
from datetime import datetime
from typing import Optional, Literal, Union
from ninja import Field, Query
from pydantic import EmailStr
from django.utils import timezone

from core.types import Unset
from processing.orchestration.attention import attention_filter, latest_run_status_subquery
from interfaces.api.schemas import (
    OrderByField,
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    WorkspaceSummaryResponse
)
from interfaces.api.schemas.orchestration.schedule import ScheduleResponse, SchedulePostBody, SchedulePatchBody


class DataConnectionOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    timestamp_key = ("timestampKey", "payload__timestamp_key")
    timestamp_format = ("timestampFormat", "payload__timestamp_format")
    timezone_type = ("timezoneType", "timezone_type")
    timezone = ("timezone", "timezone")
    workspace_id = ("workspaceId", "workspace_id")
    workspace_name = ("workspaceName", "workspace__name")


class DataConnectionQueryParameters(CollectionQueryParameters):
    order_by: list[DataConnectionOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
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
            "next_run_at": None,
        }

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
    workspace: WorkspaceSummaryResponse
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
