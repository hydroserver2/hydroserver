import uuid
from typing import Optional, Literal, Union
from ninja import Field, Query
from pydantic import EmailStr

from core.types import Unset
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
    timestamp_key = ("timestampKey", "timestamp_key")
    timestamp_format = ("timestampFormat", "timestamp_format")
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


class TimestampResponse(BaseGetResponse):
    timestamp_key: str = Field(alias="key")
    timestamp_format: Optional[str] = Field(None, alias="format")
    timezone_type: Optional[Literal["utc", "offset", "iana"]] = None
    timezone: Optional[str] = None


class TimestampPostBody(BasePostBody, TimestampResponse):
    ...


class TimestampPatchBody(BasePatchBody, TimestampResponse):
    ...


class CSVPayloadResponse(BaseGetResponse):
    payload_type: Literal["CSV"] = Field(alias="type")
    header_row: Optional[int] = None
    data_start_row: Optional[int] = None
    delimiter: Optional[str] = Field(None, max_length=1)


class CSVPayloadPostBody(BasePostBody, CSVPayloadResponse):
    ...


class CSVPayloadPatchBody(BasePatchBody, CSVPayloadResponse):
    ...


class JSONPayloadResponse(BaseGetResponse):
    payload_type: Literal["JSON"] = Field(alias="type")
    jmespath: Optional[str] = None


class JSONPayloadPostBody(BasePostBody, JSONPayloadResponse):
    ...


class JSONPayloadPatchBody(BasePatchBody, JSONPayloadResponse):
    ...


class PlaceholderVariableResponse(BaseGetResponse):
    name: str
    variable_type: Literal["run_time", "latest_observation_timestamp", "per_task"] = Field(alias="type")


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
    workspace: WorkspaceSummaryResponse
    timestamp: TimestampResponse
    payload: Union[CSVPayloadResponse, JSONPayloadResponse]
    placeholder_variables: list[PlaceholderVariableResponse]
    notification: Optional[NotificationResponse] = None

    @staticmethod
    def resolve_timestamp(obj):
        return {
            "timestamp_key": obj.timestamp_key,
            "timestamp_format": obj.timestamp_format,
            "timezone_type": obj.timezone_type,
            "timezone": obj.timezone,
        }

    @staticmethod
    def resolve_notification(obj):
        try:
            return obj.notification
        except Exception:
            return None


class DataConnectionPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    source_url: str
    workspace_id: uuid.UUID
    timestamp: TimestampPostBody
    payload: Union[CSVPayloadPostBody, JSONPayloadPostBody]
    placeholder_variables: list[PlaceholderVariablePostBody]
    notification: NotificationPostBody | None = None


class DataConnectionPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    source_url: str
    timestamp: TimestampPatchBody
    payload: Union[CSVPayloadPatchBody, JSONPayloadPatchBody]
    placeholder_variables: list[PlaceholderVariablePatchBody]
    notification: NotificationPatchBody | None | Unset = Unset
