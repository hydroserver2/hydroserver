import uuid
from functools import cached_property
from typing import ClassVar, TYPE_CHECKING, List, Optional, Literal, Union
from datetime import datetime
from pydantic import Field, AliasPath, AliasChoices
from ..base import HydroServerBaseModel
from .orchestration_system import OrchestrationSystem
from .data_connection import DataConnection
from .run import TaskRun


if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Task(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    task_type: Literal["ETL", "Aggregation"] = Field("ETL", alias="type")
    extractor_settings: dict = Field(default_factory=dict, alias="extractorSettings")
    transformer_settings: dict = Field(default_factory=dict, alias="transformerSettings")
    loader_settings: dict = Field(default_factory=dict, alias="loaderSettings")
    data_connection_id: Optional[uuid.UUID] = Field(
        None, validation_alias=AliasChoices("dataConnectionId", AliasPath("dataConnection", "id"))
    )
    orchestration_system_id: uuid.UUID = Field(
        None, validation_alias=AliasChoices("orchestrationSystemId", AliasPath("orchestrationSystem", "id"))
    )
    workspace_id: uuid.UUID = Field(
        None, validation_alias=AliasChoices("workspaceId", AliasPath("workspace", "id"))
    )
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    paused: bool = Field(False, validation_alias=AliasPath("schedule", "paused"))
    interval: Optional[int] = Field(None, gt=0, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Literal["minutes", "hours", "days"]] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    latest_run: Optional[TaskRun] = None
    mappings: List[dict]

    _editable_fields: ClassVar[set[str]] = {
        "name",
        "task_type",
        "extractor_settings",
        "transformer_settings",
        "loader_settings",
        "data_connection_id",
        "orchestration_system_id",
        "start_time",
        "next_run_at",
        "paused",
        "interval",
        "interval_period",
        "crontab",
        "mappings"
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.tasks, **data)

    @classmethod
    def get_route(cls):
        return "etl-tasks"

    @cached_property
    def workspace(self) -> "Workspace":
        return self.client.workspaces.get(uid=self.workspace_id)

    @cached_property
    def orchestration_system(self) -> Optional[OrchestrationSystem]:
        return self.client.orchestrationsystems.get(uid=self.orchestration_system_id)

    @cached_property
    def data_connection(self) -> Optional[DataConnection]:
        if not self.data_connection_id:
            return None
        return self.client.dataconnections.get(uid=self.data_connection_id)

    def get_task_runs(
        self,
        page: int = ...,
        page_size: int = 100,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_max: datetime = ...,
        started_at_min: datetime = ...,
        finished_at_max: datetime = ...,
        finished_at_min: datetime = ...,
    ):
        """Get a collection of task runs associated with this task."""

        return self.client.tasks.get_task_runs(
            uid=self.uid,
            page=page,
            page_size=page_size,
            order_by=order_by,
            status=status,
            started_at_max=started_at_max,
            started_at_min=started_at_min,
            finished_at_max=finished_at_max,
            finished_at_min=finished_at_min,
        )

    def create_task_run(
        self,
        status: Literal["RUNNING", "SUCCESS", "FAILURE"],
        started_at: datetime,
        finished_at: datetime = ...,
        result: dict = ...,
    ):
        """Create a new task run for this task."""

        return self.client.tasks.create_task_run(
            uid=self.uid,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
        )

    def get_task_run(
        self,
        uid: Union[uuid.UUID, str],
    ):
        """Get a task run record for this task."""

        return self.client.tasks.get_task_run(uid=self.uid, task_run_id=uid)

    def update_task_run(
        self,
        uid: Union[uuid.UUID, str],
        status: Literal["RUNNING", "SUCCESS", "FAILURE"] = ...,
        started_at: datetime = ...,
        finished_at: datetime = ...,
        result: dict = ...,
    ):
        """Update a task run record of this task."""

        return self.client.tasks.update_task_run(
            uid=self.uid,
            task_run_id=uid,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
        )

    def delete_task_run(
        self,
        uid: Union[uuid.UUID, str],
    ):
        """Delete a task run record of this task."""

        return self.client.tasks.delete_task_run(uid=self.uid, task_run_id=uid)

    def run(self):
        """Trigger HydroServer to run this task."""

        return self.client.tasks.run(uid=self.uid)
