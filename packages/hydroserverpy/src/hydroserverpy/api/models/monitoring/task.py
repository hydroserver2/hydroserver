import uuid
from datetime import datetime
from functools import cached_property
from typing import ClassVar, List, Literal, Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, AliasPath
from pydantic.alias_generators import to_camel
from ..base import HydroServerBaseModel
from ..orchestration.run import TaskRun

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class MonitoringRuleInline(BaseModel):
    id: uuid.UUID
    rule_type: str
    last_checked_at: Optional[datetime] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[Literal["minutes", "hours", "days"]] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MonitoredDatastream(BaseModel):
    datastream_id: uuid.UUID = Field(..., validation_alias=AliasPath("datastream", "id"))
    datastream_name: str = Field(..., validation_alias=AliasPath("datastream", "name"))
    rules: List[MonitoringRuleInline] = []

    model_config = ConfigDict(populate_by_name=True)


class MonitoringTask(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID = Field(..., validation_alias=AliasPath("thing", "id"))
    thing_name: str = Field(..., validation_alias=AliasPath("thing", "name"))
    enabled: Optional[bool] = Field(None, validation_alias=AliasPath("schedule", "enabled"))
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    interval: Optional[int] = Field(None, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Literal["minutes", "hours", "days"]] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    latest_run: Optional[TaskRun] = None
    monitored_datastreams: List[MonitoredDatastream] = []
    recipients: List[str] = []

    _editable_fields: ClassVar[set[str]] = {
        "name",
        "description",
        "recipients",
        "enabled",
        "crontab",
        "interval",
        "interval_period",
        "start_time",
        "next_run_at",
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.monitoringtasks, **data)

    @classmethod
    def get_route(cls):
        return "monitoring/tasks"

    @cached_property
    def rules(self):
        """All monitoring rules for this task."""

        return self.client.monitoringrules.list(task_id=self.uid, fetch_all=True).items

    def trigger(self) -> TaskRun:
        """Trigger an immediate run of this monitoring task."""

        return self.client.monitoringtasks.trigger(uid=self.uid)

    def list_runs(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_min: datetime = ...,
        started_at_max: datetime = ...,
        finished_at_min: datetime = ...,
        finished_at_max: datetime = ...,
    ) -> List[TaskRun]:
        """Get a collection of task runs for this monitoring task."""

        return self.client.monitoringtasks.list_runs(
            uid=self.uid,
            page=page,
            page_size=page_size,
            order_by=order_by,
            status=status,
            started_at_min=started_at_min,
            started_at_max=started_at_max,
            finished_at_min=finished_at_min,
            finished_at_max=finished_at_max,
        )

    def get_run(self, run_id: uuid.UUID) -> TaskRun:
        """Get a single task run for this monitoring task."""

        return self.client.monitoringtasks.get_run(uid=self.uid, run_id=run_id)
