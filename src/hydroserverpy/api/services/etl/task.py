import json
from typing import Literal, Union, Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from hydroserverpy.api.models import DataConnection, Task, TaskRun, TaskMapping, OrchestrationSystem
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class TaskService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Task
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        task_type: str = ...,
        orchestration_system: Optional[Union["OrchestrationSystem", UUID, str]] = ...,
        orchestration_system_type: str = ...,
        data_connection: Union["Workspace", UUID, str] = ...,
        data_connection_type: str = ...,
        extractor_type: str = ...,
        transformer_type: str = ...,
        loader_type: str = ...,
        source_identifier: str = ...,
        target_identifier: str = ...,
        latest_run_status: str = ...,
        latest_run_started_at_max: datetime = ...,
        latest_run_started_at_min: datetime = ...,
        latest_run_finished_at_max: Optional[datetime] = ...,
        latest_run_finished_at_min: Optional[datetime] = ...,
        start_time_max: Optional[datetime] = ...,
        start_time_min: Optional[datetime] = ...,
        next_run_at_max: Optional[datetime] = ...,
        next_run_at_min: Optional[datetime] = ...,
        paused: bool = ...,
        fetch_all: bool = False,
    ) -> List["Task"]:
        """Fetch a collection of ETL tasks."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            type=task_type,
            orchestration_system_id=normalize_uuid(orchestration_system),
            orchestration_system_type=orchestration_system_type,
            data_connection_id=normalize_uuid(data_connection),
            data_connection_type=data_connection_type,
            extractor_type=extractor_type,
            transformer_type=transformer_type,
            loader_type=loader_type,
            source_identifier=source_identifier,
            target_identifier=target_identifier,
            latest_run_status=latest_run_status,
            latest_run_started_at_max=latest_run_started_at_max,
            latest_run_started_at_min=latest_run_started_at_min,
            latest_run_finished_at_max=latest_run_finished_at_max,
            latest_run_finished_at_min=latest_run_finished_at_min,
            start_time_max=start_time_max,
            start_time_min=start_time_min,
            next_run_at_max=next_run_at_max,
            next_run_at_min=next_run_at_min,
            paused=paused,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        workspace: Union["Workspace", UUID, str],
        orchestration_system: Union["OrchestrationSystem", UUID, str],
        data_connection: Optional[Union["DataConnection", UUID, str]] = None,
        task_type: str = "ETL",
        extractor_variables: Optional[dict] = None,
        transformer_variables: Optional[dict] = None,
        loader_variables: Optional[dict] = None,
        paused: bool = False,
        start_time: Optional[datetime] = None,
        next_run_at: Optional[datetime] = None,
        crontab: Optional[str] = None,
        interval: Optional[int] = None,
        interval_period: Optional[str] = None,
        mappings: Optional[List[dict]] = None,
        uid: Optional[UUID] = None,
    ) -> "Task":
        """Create a new ETL task."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "type": task_type,
            "workspaceId": normalize_uuid(workspace),
            "dataConnectionId": normalize_uuid(data_connection),
            "orchestrationSystemId": normalize_uuid(orchestration_system),
            "extractorVariables": extractor_variables or {},
            "transformerVariables": transformer_variables or {},
            "loaderVariables": loader_variables or {},
            "mappings": mappings or [],
        }

        # Only include schedule if the caller provided scheduling information.
        # Using Ellipsis here breaks JSON serialization.
        if interval or crontab:
            body["schedule"] = {
                "paused": paused,
                "startTime": start_time,
                "nextRunAt": next_run_at,
                "crontab": crontab,
                "interval": interval,
                "intervalPeriod": interval_period,
            }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        task_type: str = ...,
        name: str = ...,
        data_connection: Optional[Union["DataConnection", UUID, str]] = ...,
        orchestration_system: Union["OrchestrationSystem", UUID, str] = ...,
        extractor_variables: dict = ...,
        transformer_variables: dict = ...,
        loader_variables: dict = ...,
        paused: bool = ...,
        start_time: Optional[datetime] = ...,
        next_run_at: Optional[datetime] = ...,
        crontab: Optional[str] = ...,
        interval: Optional[int] = ...,
        interval_period: Optional[str] = ...,
        mappings: List[dict] = ...
    ) -> "DataConnection":
        """Update an ETL task."""

        body: Dict[str, Any] = {
            "type": task_type,
            "name": name,
            "dataConnectionId": normalize_uuid(data_connection),
            "orchestrationSystemId": normalize_uuid(orchestration_system),
            "extractorVariables": extractor_variables,
            "transformerVariables": transformer_variables,
            "loaderVariables": loader_variables,
            "mappings": mappings
        }

        if crontab is None and interval is None:
            body["schedule"] = None
        elif any(value is not ... for value in [paused, start_time, next_run_at, crontab, interval, interval_period]):
            body["schedule"] = {
                "paused": paused,
                "startTime": start_time,
                "nextRunAt": next_run_at,
                "crontab": crontab,
                "interval": interval,
                "intervalPeriod": interval_period,
            }

        return super().update(uid=str(uid), **body)

    def run(self, uid: Union[UUID, str]):
        """Run an ETL task."""

        self.client.request(
            "post", f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}"
        )

    def get_task_runs(
        self,
        uid: Union[UUID, str],
        page: int = ...,
        page_size: int = 100,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_max: datetime = ...,
        started_at_min: datetime = ...,
        finished_at_max: datetime = ...,
        finished_at_min: datetime = ...,
    ) -> List["TaskRun"]:
        """Retrieve task runs of a task."""

        params = {
            "page": page,
            "page_size": page_size,
            "order_by": ",".join(order_by) if order_by is not ... else order_by,
            "status": status,
            "started_at_max": started_at_max,
            "started_at_min": started_at_min,
            "finished_at_max": finished_at_max,
            "finished_at_min": finished_at_min,
        }
        params = {
            k: ("null" if v is None else v)
            for k, v in params.items()
            if v is not ...
        }

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs"

        return [
            TaskRun(**task_run) for task_run in self.client.request("get", path, params=params).json()
        ]

    def create_task_run(
        self,
        uid: Union[UUID, str],
        status: Literal["RUNNING", "SUCCESS", "FAILURE"],
        started_at: datetime,
        finished_at: datetime = ...,
        result: dict = ...,
    ) -> TaskRun:
        """Create a task run record for a task."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs"
        headers = {"Content-type": "application/json"}
        body = {
            k: ("null" if v is None else v) for k, v in {
                "status": status,
                "started_at": started_at,
                "finished_at": finished_at,
                "result": result,
            }.items() if v is not ...
        }

        return TaskRun(**self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json())

    def get_task_run(
        self,
        uid: Union[UUID, str],
        task_run_id: Union[UUID, str]
    ) -> TaskRun:
        """Get a task run record for a task."""

        return TaskRun(**self.client.request(
            "get", f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs/{str(task_run_id)}"
        ).json())

    def update_task_run(
        self,
        uid: Union[UUID, str],
        task_run_id: Union[UUID, str],
        status: Literal["RUNNING", "SUCCESS", "FAILURE"] = ...,
        started_at: datetime = ...,
        finished_at: datetime = ...,
        result: dict = ...,
    ) -> TaskRun:
        """Update a task run record for a task."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs/{str(task_run_id)}"
        headers = {"Content-type": "application/json"}
        body = {
            k: ("null" if v is None else v) for k, v in {
                "status": status,
                "started_at": started_at,
                "finished_at": finished_at,
                "result": result,
            }.items() if v is not ...
        }

        return TaskRun(**self.client.request(
            "patch", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json())

    def delete_task_run(
        self,
        uid: Union[UUID, str],
        task_run_id: Union[UUID, str]
    ) -> None:
        """Delete a task run record for a task."""

        self.client.request(
            "delete", f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs/{str(task_run_id)}"
        )
