import uuid
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union, TYPE_CHECKING
from pydantic import Field, AliasPath
from ..base import HydroServerBaseModel
from ..orchestration.run import TaskRun
from .mapping import EtlMapping

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from .data_connection import DataConnection


class EtlTask(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    task_variables: Dict[str, Any] = Field(default_factory=dict)
    data_connection_id: uuid.UUID = Field(..., validation_alias=AliasPath("dataConnection", "id"))
    enabled: Optional[bool] = Field(None, validation_alias=AliasPath("schedule", "enabled"))
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    interval: Optional[int] = Field(None, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Literal["minutes", "hours", "days"]] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    latest_run: Optional[TaskRun] = None
    mappings: List[EtlMapping] = []

    _editable_fields: ClassVar[set[str]] = set()

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.etltasks, **data)

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.service:
            raise NotImplementedError("Saving not enabled for this object.")

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        saved_resource = self.service.update(
            self.uid,
            name=self.name,
            description=self.description,
            task_variables=self.task_variables,
            mappings=[
                {"source_identifier": m.source_identifier, "target_datastream_id": str(m.target_datastream.id)}
                for m in self.mappings
            ],
            crontab=self.crontab,
            interval=self.interval,
            interval_period=self.interval_period,
            start_time=self.start_time,
            enabled=self.enabled,
        )
        self._server_data = saved_resource.dict(by_alias=False).copy()
        self.__dict__.update(saved_resource.__dict__)

    @classmethod
    def get_route(cls):
        return "etl/tasks"

    @property
    def data_connection(self) -> "DataConnection":
        """Fetch the DataConnection associated with this task."""

        return self.client.dataconnections.get(uid=self.data_connection_id)

    def trigger(self) -> TaskRun:
        """Trigger an immediate run of this ETL task."""

        return self.client.etltasks.trigger(uid=self.uid)

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
        """Get a collection of task runs for this ETL task."""

        return self.client.etltasks.list_runs(
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

    def get_run(self, run_id: Union[uuid.UUID, str]) -> TaskRun:
        """Get a single task run for this ETL task."""

        return self.client.etltasks.get_run(uid=self.uid, run_id=run_id)
