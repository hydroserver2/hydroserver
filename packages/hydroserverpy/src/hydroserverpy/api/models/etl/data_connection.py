import uuid
from datetime import datetime
from typing import ClassVar, List, Literal, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, AliasPath
from pydantic.alias_generators import to_camel
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class CSVPayload(BaseModel):
    payload_type: Literal["CSV"] = Field(..., alias="type")
    timestamp_key: str
    timestamp_format: Optional[str] = None
    header_row: Optional[int] = None
    data_start_row: Optional[int] = None
    delimiter: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class JSONPayload(BaseModel):
    payload_type: Literal["JSON"] = Field(..., alias="type")
    timestamp_key: str
    timestamp_format: Optional[str] = None
    jmespath: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PlaceholderVariable(BaseModel):
    name: str
    variable_type: Literal["run_time", "latest_observation_timestamp", "per_task"] = Field(..., alias="type")
    timestamp_format: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class NotificationSchedule(BaseModel):
    enabled: bool = True
    start_time: Optional[datetime] = None
    crontab: Optional[str] = None
    interval: Optional[int] = None
    interval_period: Optional[Literal["minutes", "hours", "days"]] = None
    next_run_at: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Notification(BaseModel):
    schedule: Optional[NotificationSchedule] = None
    recipient_emails: List[str] = []

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DataConnection(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    source_url: str
    workspace_id: uuid.UUID = Field(..., validation_alias=AliasPath("workspace", "id"))
    workspace_name: str = Field(..., validation_alias=AliasPath("workspace", "name"))
    timezone_type: Optional[Literal["offset", "iana"]] = None
    timezone: Optional[str] = None
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None
    payload: Union[CSVPayload, JSONPayload]
    placeholder_variables: List[PlaceholderVariable] = []
    notification: Optional[Notification] = None
    task_count: int = 0
    task_attention_count: int = 0

    _editable_fields: ClassVar[set[str]] = set()

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.dataconnections, **data)

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.service:
            raise NotImplementedError("Saving not enabled for this object.")

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        saved_resource = self.service.update(
            self.uid,
            name=self.name,
            source_url=self.source_url,
            payload_type=self.payload.payload_type,
            description=self.description,
            timestamp_key=getattr(self.payload, "timestamp_key"),
            timestamp_format=getattr(self.payload, "timestamp_format", None),
            timezone_type=self.timezone_type,
            timezone=self.timezone,
            header_row=getattr(self.payload, "header_row", None),
            data_start_row=getattr(self.payload, "data_start_row", None),
            delimiter=getattr(self.payload, "delimiter", None),
            jmespath=getattr(self.payload, "jmespath", None),
            placeholder_variables=[pv.model_dump(by_alias=False) for pv in self.placeholder_variables],
            notification=self.notification.model_dump(by_alias=False) if self.notification else None,
        )
        self._server_data = saved_resource.dict(by_alias=False).copy()
        self.__dict__.update(saved_resource.__dict__)

    @classmethod
    def get_route(cls):
        return "etl/data-connections"
